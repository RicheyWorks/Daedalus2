package com.terpenepirate.imageoptimizer.bridge;

import com.terpenepirate.imageoptimizer.ImageOptimizationService;
import com.terpenepirate.imageoptimizer.OptimizationJobService;
import com.terpenepirate.imageoptimizer.OptimizationPlan;
import javax.imageio.ImageIO;
import java.awt.Color;
import java.awt.image.BufferedImage;
import java.io.*;
import java.net.URI;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.security.MessageDigest;
import java.time.*;
import java.util.*;
import java.util.regex.*;

/** Evidence-only runner. No application source modifications, editor calls or external services. */
public final class ImageWorkspaceAcceptance {
    private static final String SOURCE = "bdd47836cedb5c5261d281cb4ab132a1e89fcb91";
    private static final HttpClient HTTP = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2))
            .followRedirects(HttpClient.Redirect.NEVER).proxy(new java.net.ProxySelector() {
                public List<java.net.Proxy> select(URI uri) { return List.of(java.net.Proxy.NO_PROXY); }
                public void connectFailed(URI uri, java.net.SocketAddress address, IOException failure) {}
            }).build();
    private static Path root;
    private static final List<String> checks = new ArrayList<>();
    private static int wireCalls;

    public static void main(String[] args) throws Exception {
        if (args.length != 2 || !Set.of("run", "verify-persisted", "serve", "serve-smoke").contains(args[0]))
            throw new IllegalArgumentException("Use run|verify-persisted|serve|serve-smoke and the evidence directory");
        root = Path.of(args[1]).toAbsolutePath().normalize(); Files.createDirectories(root);
        try {
            switch (args[0]) {
                case "run" -> conversion();
                case "verify-persisted" -> persistence();
                case "serve" -> serve(false);
                case "serve-smoke" -> serve(true);
            }
        } catch (Throwable failure) {
            // Do not print request headers, pairing URIs, capabilities or source exception text.
            Files.writeString(root.resolve("last-failure.txt"), failure.getClass().getName() + " at " + Instant.now());
            throw new IllegalStateException("Synthetic acceptance did not complete; see the local failure class receipt");
        }
    }
    private static void require(boolean value, String label) {
        if (!value) throw new AssertionError(label);
        checks.add(label);
    }
    private static String hash(byte[] bytes) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }
    private static String fileHash(Path path) throws Exception { return hash(Files.readAllBytes(path)); }
    private static String field(String json, String name) {
        Matcher match = Pattern.compile("\"" + name + "\":\"([^\"]*)\"").matcher(json);
        if (!match.find()) throw new AssertionError("Missing expected JSON field");
        return match.group(1);
    }
    private static void jsonCheck(String json) {
        require(json.getBytes(StandardCharsets.UTF_8).length < 131072, "JSON within native 128KiB budget");
        require(!json.contains(root.toString()) && !json.contains("approved-source") && !json.contains("approved-output"), "wire response contains no source/destination paths");
    }
    private static String call(RealmImageBridge bridge, RealmImageWorkspace.Grant grant, String method,
                               String path, String key, int expected) throws Exception {
        var response = bytes(bridge, grant, method, path, key);
        require(response.statusCode() == expected, method + " " + path + " HTTP " + expected);
        String json = new String(response.body(), StandardCharsets.UTF_8); jsonCheck(json); return json;
    }
    private static HttpResponse<byte[]> bytes(RealmImageBridge bridge, RealmImageWorkspace.Grant grant,
                                             String method, String path, String key) throws Exception {
        URI uri = bridge.baseUri().resolve(path);
        if (!uri.getHost().equals("127.0.0.1")) throw new AssertionError("Literal loopback required");
        var request = HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(6));
        if (grant != null) request.header("Authorization", "Bearer " + grant.launchUri().getFragment().substring(6));
        if (key != null) request.header("Idempotency-Key", key);
        request.method(method, HttpRequest.BodyPublishers.noBody());
        wireCalls++; return HTTP.send(request.build(), HttpResponse.BodyHandlers.ofByteArray());
    }
    private static void fixture(Path path, int width, int height, boolean alpha, boolean noise) throws Exception {
        Files.createDirectories(path.getParent());
        var image = new BufferedImage(width, height, alpha ? BufferedImage.TYPE_INT_ARGB : BufferedImage.TYPE_INT_RGB);
        Random random = new Random(153);
        for (int y=0; y<height; y++) for (int x=0; x<width; x++)
            image.setRGB(x,y,noise ? random.nextInt() : alpha && y<height/4 ? 0x00ffffff : x<width/2 ? Color.RED.getRGB() : Color.BLUE.getRGB());
        try { if (!ImageIO.write(image, path.toString().endsWith("jpg") ? "jpg" : "png", path.toFile())) throw new IOException(); }
        finally { image.flush(); }
    }
    private static OptimizationJobService.Settings settings() { return new OptimizationJobService.Settings(false,true,64,.85,true,true); }
    private static String settled(RealmImageBridge bridge, RealmImageWorkspace.Grant grant, String id) throws Exception {
        Instant until = Instant.now().plusSeconds(8);
        while (Instant.now().isBefore(until)) {
            String response = call(bridge, grant, "GET", "/v1/workspace/actions/"+id, null, 200);
            if (Set.of("SUCCEEDED","FAILED","CANCELED").contains(field(response,"state"))) return response;
            Thread.sleep(20);
        }
        throw new AssertionError("Bounded fixture action did not settle");
    }
    private static void conversion() throws Exception {
        Path run = Files.createDirectory(root.resolve("run-"+UUID.randomUUID()));
        Path source = run.resolve("approved-source"), output = Files.createDirectory(run.resolve("approved-output"));
        fixture(source.resolve("a/photo.png"),160,80,true,false);
        Files.createDirectories(source.resolve("b")); Files.copy(source.resolve("a/photo.png"),source.resolve("b/copy.png"));
        fixture(source.resolve("c/photo.jpg"),120,60,false,false);
        fixture(source.resolve("d/existing.png"),96,64,true,true);
        fixture(output.resolve("d/existing.png"),96,64,false,false);
        require(Files.size(output.resolve("d/existing.png")) < Files.size(source.resolve("d/existing.png"))*.95, "fixture satisfies original 95-percent skip heuristic");
        Properties saved = new Properties();
        try(var files=Files.walk(source)) {
            for(Path path:files.filter(Files::isRegularFile).toList()) saved.setProperty("source."+root.relativize(path).toString().replace('\\','/'),fileHash(path));
        }
        String existingHash=fileHash(output.resolve("d/existing.png"));
        try(var bridge = new RealmImageBridge()) {
            var plan=OptimizationPlan.approved(List.of(source.toFile()),output,false);
            var grant=bridge.approveWorkspace(plan,settings());
            require(grant.launchUri().toString().matches("http://127\\.0\\.0\\.1:[1-9][0-9]{0,4}/realm/image-workspace/#token=[A-Za-z0-9_-]{43}"), "native typed workspace URI grammar");
            require(bridge.baseUri().getPort()>0, "test-owned ephemeral loopback port");
            Files.writeString(run.resolve("capabilities.json"),call(bridge,grant,"GET","/v1/workspace/capabilities",null,200));
            String initial=call(bridge,grant,"GET","/v1/workspace/plan",null,200); Files.writeString(run.resolve("plan-before.json"),initial);
            require(initial.contains("\"actionId\":null") && initial.contains("\"total\":4"),"approval starts no work and freezes four selected images");
            call(bridge,null,"GET","/v1/workspace/plan",null,401);
            call(bridge,grant,"GET","/v1/capabilities",null,401);
            String key="synthetic_acceptance_"+UUID.randomUUID();
            String started=call(bridge,grant,"POST","/v1/workspace/actions",key,202),id=field(started,"id");
            require(field(call(bridge,grant,"POST","/v1/workspace/actions",key,200),"id").equals(id),"same-key native retry retains exact action ID");
            call(bridge,grant,"POST","/v1/workspace/actions","different_action_key",409);
            String done=settled(bridge,grant,id); Files.writeString(run.resolve("action-terminal.json"),done);
            require(field(done,"state").equals("SUCCEEDED"),"actual app job reports SUCCEEDED");
            require(done.contains("\"optimized\":2")&&done.contains("\"skippedDuplicate\":1")&&done.contains("\"skippedExisting\":1")&&done.contains("\"failed\":0"),"actual optimized/duplicate/existing-skip counts are 2/1/1 with zero failures");
            require(Files.exists(output.resolve("a/photo.png")) && Files.exists(output.resolve("c/photo.jpg")) && !Files.exists(output.resolve("b/copy.png")),"relative layout preserved and duplicate creates no destination");
            require(existingHash.equals(fileHash(output.resolve("d/existing.png"))),"preexisting approved output preserved byte-for-byte");
            Pattern pattern=Pattern.compile("\\{\"index\":([0-9]+),\"name\":\"([^\"]+)\",\"format\":\"([^\"]+)\",\"width\":([0-9]+),\"height\":([0-9]+),\"bytes\":([0-9]+),\"sourceBytes\":([0-9]+),\"sha256\":\"([a-f0-9]{64})\",\"downloadPath\":\"([^\"]+)\"\\}");
            Matcher exports=pattern.matcher(done); int count=0;
            Path downloads=Files.createDirectory(run.resolve("verified-downloads"));
            while(exports.find()) {
                int index=Integer.parseInt(exports.group(1)); String name=exports.group(2), format=exports.group(3),sha=exports.group(8),path=exports.group(9);
                require(name.equals("workspace-image-"+index+"."+format)&&path.equals("/v1/workspace/actions/"+id+"/outputs/"+index),"generated output name and same-action download route");
                var response=bytes(bridge,grant,"GET",path,null);
                require(response.statusCode()==200,"actual indexed export HTTP 200");
                require(response.headers().firstValue("Cache-Control").orElse("").equals("no-store"),"export no-store header");
                require(response.headers().firstValue("Content-Type").orElse("").equals(format.equals("png")?"image/png":"image/jpeg"),"export exact PNG/JPEG content type");
                require(response.body().length==Long.parseLong(exports.group(6))&&sha.equals(hash(response.body())),"export exact declared byte length and SHA256");
                var image=ImageIO.read(new ByteArrayInputStream(response.body()));
                require(image!=null&&image.getWidth()==Integer.parseInt(exports.group(4))&&image.getHeight()==Integer.parseInt(exports.group(5)),"export decoder confirms declared dimensions");
                if(index==1 || index==3) {
                    require(image.getWidth()==64&&image.getHeight()==32,"resize actually produces 64x32 pixels");
                    Color red=new Color(image.getRGB(16,24)),blue=new Color(image.getRGB(48,24));
                    require(red.getRed()>220&&red.getBlue()<30&&blue.getBlue()>220&&blue.getRed()<30,"decoded export red/blue pixels match synthetic source");
                    if(index==1)require(image.getColorModel().hasAlpha()&&(image.getRGB(16,1)>>>24)==0,"PNG alpha survives actual export");
                }
                image.flush(); Files.write(downloads.resolve(name),response.body()); count++;
            }
            require(count==3,"two new outputs plus one verified existing skip export");
            String terminalAgain=call(bridge,grant,"POST","/v1/workspace/actions",key,200);
            require(field(terminalAgain,"id").equals(id),"completed action cannot rerun under same key");
            call(bridge,grant,"DELETE","/v1/workspace/actions/"+id,null,200);
            require(field(call(bridge,grant,"GET","/v1/workspace/actions/"+id,null,200),"state").equals("SUCCEEDED"),"cancel after success preserves honest terminal state");
            call(bridge,grant,"DELETE","/v1/workspace/grant",null,200);
            call(bridge,grant,"GET","/v1/workspace/plan",null,401);
            require(!bridge.isWorkspaceActive(grant.planId()),"revoke removes live workspace authority");
        }
        for(String key:saved.stringPropertyNames()) require(saved.getProperty(key).equals(fileHash(root.resolve(key.substring(7)))),"source SHA256 unchanged after conversion/revocation/shutdown");
        try(var files=Files.walk(output)) {
            for(Path path:files.filter(Files::isRegularFile).toList()) saved.setProperty("output."+root.relativize(path).toString().replace('\\','/'),fileHash(path));
        }
        require(saved.stringPropertyNames().stream().filter(k->k.startsWith("output.")).count()==3,"three committed files persist after service shutdown");
        try(var files=Files.walk(output)) { require(files.noneMatch(p->p.getFileName().toString().startsWith(".image-job-")||p.toString().endsWith(".part")),"no owned encoding staging/partial remains"); }
        try(var stream=Files.newOutputStream(root.resolve("persistence-manifest.properties"),StandardOpenOption.CREATE_NEW)){saved.store(stream,"Generated synthetic files only; no credentials or private links");}
        Files.writeString(root.resolve("run-result.json"),"{\"status\":\"PASS\",\"sourceCommit\":\""+SOURCE+"\",\"mode\":\"headless_programmatic_synthetic_approval\",\"runtimeAcceptance\":false,\"wireCalls\":"+wireCalls+",\"checks\":"+checks.size()+",\"runDirectory\":\""+run.getFileName()+"\",\"guiSelectionVerified\":false,\"nativePairingVerified\":false}");
        Files.write(root.resolve("checks.txt"),checks); System.out.println("PASS synthetic service conversion/export/revoke/shutdown; checks="+checks.size()+" wireCalls="+wireCalls);
    }
    private static void persistence() throws Exception {
        Properties manifest=new Properties(); try(var stream=Files.newInputStream(root.resolve("persistence-manifest.properties"))){manifest.load(stream);}
        int sources=0,outputs=0;
        for(String key:manifest.stringPropertyNames()) {
            boolean source=key.startsWith("source."); String relative=key.substring(7);
            Path path=root.resolve(relative).normalize(); require(path.startsWith(root),"manifest path remains inside evidence");
            require(manifest.getProperty(key).equals(fileHash(path)),"fresh JVM confirms persisted SHA256");
            if(source)sources++;else outputs++;
        }
        require(sources==4&&outputs==3,"fresh JVM verifies all four unchanged sources and three committed outputs");
        Files.writeString(root.resolve("persistence-result.json"),"{\"status\":\"PASS\",\"separateJvm\":true,\"unchangedSources\":4,\"persistedOutputs\":3,\"durableJobHistoryClaim\":false}");
        System.out.println("PASS separate-JVM persistence: unchangedSources=4 persistedOutputs=3; no durable job-history claim");
    }
    private static void privateDirectory(Path directory) throws IOException {
        var posix=Files.getFileAttributeView(directory,PosixFileAttributeView.class);
        if(posix!=null){posix.setPermissions(PosixFilePermissions.fromString("rwx------"));return;}
        var acl=Files.getFileAttributeView(directory,AclFileAttributeView.class);
        if(acl==null)throw new IOException();
        acl.setAcl(List.of(AclEntry.newBuilder().setType(AclEntryType.ALLOW).setPrincipal(acl.getOwner())
                .setPermissions(EnumSet.allOf(AclEntryPermission.class)).setFlags(AclEntryFlag.DIRECTORY_INHERIT,AclEntryFlag.FILE_INHERIT).build()));
    }
    private static void serve(boolean smoke) throws Exception {
        Path run=Files.createDirectory(root.resolve("live-fixture-"+UUID.randomUUID())); privateDirectory(run);
        Path source=run.resolve("approved-source"),output=Files.createDirectory(run.resolve("approved-output"));
        fixture(source.resolve("synthetic-alpha.png"),160,80,true,false);
        Path link=run.resolve("pairing-link.txt"),ready=run.resolve("ready.json");
        int ownedPort=0;
        var workspace=new RealmImageWorkspace(new OptimizationJobService(),Duration.ofSeconds(90));
        try(var bridge=new RealmImageBridge(new ImageOptimizationService(),Duration.ofSeconds(90),Duration.ofSeconds(6),workspace)) {
            ownedPort=bridge.baseUri().getPort();
            var grant=bridge.approveWorkspace(OptimizationPlan.approved(List.of(source.toFile()),output,false),settings());
            // Explicitly authorized, owner-only transient local operator handoff. Never print token or full link.
            Files.writeString(link,grant.launchUri().toASCIIString(),StandardOpenOption.CREATE_NEW);
            require(Files.readString(link).equals(grant.launchUri().toASCIIString()),"owner-only transient file contains exact fresh fixture link");
            var acl=Files.getFileAttributeView(link,AclFileAttributeView.class);
            if(acl!=null){var owner=acl.getOwner();require(!acl.getAcl().isEmpty()&&acl.getAcl().stream().allMatch(entry->entry.principal().equals(owner)),"transient pairing-file ACL contains owner only");}
            Files.writeString(ready,"{\"state\":\"READY\",\"syntheticApproval\":true,\"pid\":"+ProcessHandle.current().pid()+",\"origin\":\""+bridge.baseUri()+"\",\"pairingFile\":\"pairing-link.txt\",\"selfStopSeconds\":90,\"expiresAt\":\""+grant.expiresAt()+"\"}");
            System.out.println("READY test-owned fixture; private link is in owner-only file " + run.getFileName()+"/pairing-link.txt (not printed)");
            try {
                if(smoke) {
                    call(bridge,grant,"GET","/v1/workspace/capabilities",null,200);
                    call(bridge,grant,"GET","/v1/workspace/plan",null,200);
                    call(bridge,grant,"DELETE","/v1/workspace/grant",null,200);
                } else {
                    long until=System.nanoTime()+Duration.ofSeconds(90).toNanos();
                    while(System.nanoTime()<until && bridge.isWorkspaceActive(grant.planId()) && !Files.exists(run.resolve("stop.request"))) Thread.sleep(200);
                }
            } finally { Files.deleteIfExists(link); }
        } finally {
            Files.deleteIfExists(link); Files.writeString(ready,"{\"state\":\"STOPPED\",\"privatePairingFileRemoved\":true,\"syntheticApproval\":true}");
        }
        if(smoke) {
            boolean refused=false;
            try(var probe=new java.net.Socket()){probe.connect(new java.net.InetSocketAddress("127.0.0.1",ownedPort),500);}
            catch(IOException closed){refused=true;}
            require(refused,"test-owned listener refuses connection after clean close");
            require(!Files.exists(link),"transient pairing file removed after clean close");
            Files.writeString(root.resolve("serve-smoke-result.json"),"{\"status\":\"PASS\",\"fixtureDirectory\":\""+run.getFileName()+"\",\"actualListenerAndCapabilitiesAndPlan\":true,\"revokeAndCleanClose\":true,\"privateLinkRemoved\":true,\"postCloseConnectionRefused\":true,\"leftRunning\":false}");
        }
        System.out.println("STOPPED test-owned service; transient link file deleted; committed fixture outputs, if any, retained");
    }
}
