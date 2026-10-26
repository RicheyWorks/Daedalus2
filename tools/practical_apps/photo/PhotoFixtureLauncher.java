package com.photostopdfpc.bridge;

import com.photostopdfpc.service.ApprovedPhotoWorkspace;
import com.photostopdfpc.service.PdfConversionService;
import javax.imageio.ImageIO;
import java.awt.Color;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/** Test-only launcher of existing production bridges; no application CLI is changed. */
public final class PhotoFixtureLauncher {
    private static final int MAX_SECONDS = 120;
    private static final class Lease implements AutoCloseable {
        final AtomicBoolean closed = new AtomicBoolean();
        final Path link;
        final RealmPhotoBridge selected;
        final ApprovedPhotoWorkspace workspace;
        final RealmPhotoWorkspaceBridge approved;
        Lease(Path link, RealmPhotoBridge selected, ApprovedPhotoWorkspace workspace,
              RealmPhotoWorkspaceBridge approved) {
            this.link=link; this.selected=selected; this.workspace=workspace; this.approved=approved;
        }
        public void close() {
            if (!closed.compareAndSet(false,true)) return;
            if (approved != null) approved.close();
            if (workspace != null) workspace.close();
            if (selected != null) selected.close();
            try { Files.deleteIfExists(link); } catch (IOException ignored) { }
        }
    }
    public static void main(String[] args) throws Exception {
        long enteredNanos=System.nanoTime();
        if (args.length != 3 || !Set.of("selected","workspace","a4-portrait","a4-landscape").contains(args[0])
                || !args[1].matches("[a-z0-9-]{1,40}"))
            throw new IllegalArgumentException("Expected mode, new synthetic run name, and lifetime seconds.");
        int seconds = Integer.parseInt(args[2]);
        if (seconds < 1 || seconds > MAX_SECONDS) throw new IllegalArgumentException("Lifetime must be 1..120 seconds.");
        String mode=args[0];
        Path allowed=Path.of(Objects.requireNonNull(System.getProperty("photo.acceptanceRoot"))).toRealPath();
        if (!Files.isDirectory(allowed,LinkOption.NOFOLLOW_LINKS) || Files.isSymbolicLink(allowed))
            throw new IOException("Synthetic evidence root unavailable.");
        Path root=Files.createDirectory(allowed.resolve(args[1]));
        restrict(root,true);
        Path inputs=Files.createDirectory(root.resolve("inputs"));
        Path destination=Files.createDirectory(root.resolve("approved-output"));
        Path png=inputs.resolve("synthetic-red-blue.png"), jpeg=inputs.resolve("synthetic-red-blue.jpg");
        image(png,"png",32,24); image(jpeg,"jpeg",40,28);
        Path link=root.resolve("private-pairing-link.txt");
        RealmPhotoBridge selected=null;
        ApprovedPhotoWorkspace workspace=null;
        RealmPhotoWorkspaceBridge approved=null;
        try {
            if (mode.equals("selected")) selected=new RealmPhotoBridge();
            else {
                PdfConversionService.Layout layout=switch(mode) {
                    case "a4-portrait" -> PdfConversionService.Layout.A4_PORTRAIT;
                    case "a4-landscape" -> PdfConversionService.Layout.A4_LANDSCAPE;
                    default -> PdfConversionService.Layout.IMAGE_SIZE;
                };
                workspace=ApprovedPhotoWorkspace.freeze(List.of(png.toFile(),jpeg.toFile()),destination,layout,()->false);
                approved=RealmPhotoWorkspaceBridge.start(workspace);
            }
        } catch (Exception failure) {
            if (approved != null) approved.close(); if (workspace != null) workspace.close();
            if (selected != null) selected.close();
            throw new IOException("Synthetic bridge could not start.");
        }
        URI pairing=selected != null ? selected.pairingUri() : approved.pairingUri();
        URI origin=URI.create("http://127.0.0.1:"+pairing.getPort());
        String protocol=selected != null ? "photospdf.local.v1" : "photospdf.workspace.v1";
        Path selectedStorage=selected != null ? selected.storageRoot() : null;
        Lease lease=new Lease(link,selected,workspace,approved);
        Thread hook=new Thread(lease::close,"synthetic-photo-normal-close");
        Runtime.getRuntime().addShutdownHook(hook);
        Instant start=Instant.now();
        // Reserve ten seconds for normal cleanup (the selected bridge may await
        // its conversion worker for five seconds) under the 120-second limit;
        // time spent generating/approving fixtures consumes the same budget.
        long deadline=enteredNanos+TimeUnit.SECONDS.toNanos(Math.min(seconds,110));
        boolean capabilityOk=false, stopped=false;
        try {
            Files.writeString(link,pairing.toString(),StandardCharsets.US_ASCII,StandardOpenOption.CREATE_NEW);
            restrict(link,false);
            capabilityOk=capabilities(origin,pairing.getRawFragment().substring(6),protocol);
            if (!capabilityOk) throw new IOException("Synthetic capability check failed.");
            // Removing only this fresh link requests a normal early close; no process kill.
            while (Files.exists(link,LinkOption.NOFOLLOW_LINKS) && System.nanoTime()<deadline)
                TimeUnit.MILLISECONDS.sleep(50);
        } finally {
            lease.close(); Runtime.getRuntime().removeShutdownHook(hook);
            // Probe only the listener created by this fixture. No listener/process enumeration.
            try (Socket socket=new Socket()) {
                socket.connect(new InetSocketAddress(InetAddress.getByAddress(new byte[]{127,0,0,1}),origin.getPort()),500);
            } catch (ConnectException expected) { stopped=true; }
            catch (IOException other) { stopped=false; }
            String receipt="{\n  \"syntheticApprovalOnly\":true,\n  \"mode\":\""+mode+"\",\n"
                    +"  \"protocol\":\""+protocol+"\",\n  \"port\":"+origin.getPort()+",\n"
                    +"  \"startedUtc\":\""+start+"\",\n  \"finishedUtc\":\""+Instant.now()+"\",\n"
                    +"  \"requestedSeconds\":"+seconds+",\n  \"effectiveServiceWindowSeconds\":"+Math.min(seconds,110)+",\n  \"normalCleanupBudgetSeconds\":10,\n  \"capabilitiesHttp200AndProtocol\":"+capabilityOk+",\n"
                    +"  \"postCloseConnectionRefused\":"+stopped+",\n  \"linkRemoved\":"+!Files.exists(link)+",\n"
                    +"  \"selectedPrivateStorageRemoved\":"+(selectedStorage==null ? "null" : Boolean.toString(!Files.exists(selectedStorage)))+",\n"
                    +"  \"nativeOrInstalledGuiRun\":false,\n  \"autoStartConversion\":false\n}\n";
            Files.writeString(root.resolve("lifecycle.json"),receipt,StandardOpenOption.CREATE_NEW);
        }
        if (!capabilityOk || !stopped) throw new IOException("Synthetic lifecycle check failed.");
        System.out.println("Synthetic Photo fixture stopped normally; see its lifecycle.json.");
    }
    private static boolean capabilities(URI origin,String token,String protocol) throws Exception {
        ProxySelector direct=new ProxySelector() {
            public List<Proxy> select(URI uri) { return List.of(Proxy.NO_PROXY); }
            public void connectFailed(URI uri,SocketAddress address,IOException failure) { }
        };
        try (HttpClient client=HttpClient.newBuilder().proxy(direct).followRedirects(HttpClient.Redirect.NEVER)
                .connectTimeout(Duration.ofSeconds(1)).build()) {
            HttpRequest request=HttpRequest.newBuilder(origin.resolve("/v1/capabilities"))
                    .timeout(Duration.ofSeconds(3)).header("Authorization","Bearer "+token).GET().build();
            var response=client.send(request,HttpResponse.BodyHandlers.ofInputStream());
            try (var body=response.body()) {
                byte[] bytes=body.readNBytes(32769);
                return response.statusCode()==200 && bytes.length<=32768
                        && new String(bytes,StandardCharsets.UTF_8).contains("\"protocol\":\""+protocol+"\"");
            }
        }
    }
    private static void image(Path path,String format,int width,int height) throws IOException {
        BufferedImage image=new BufferedImage(width,height,BufferedImage.TYPE_INT_RGB);
        try {
            for(int y=0;y<height;y++) for(int x=0;x<width;x++)
                image.setRGB(x,y,x<width/2 ? Color.RED.getRGB() : Color.BLUE.getRGB());
            try(var output=Files.newOutputStream(path,StandardOpenOption.CREATE_NEW)) {
                if(!ImageIO.write(image,format,output)) throw new IOException("Synthetic image encoder unavailable.");
            }
        } finally { image.flush(); }
    }
    private static void restrict(Path path,boolean directory) throws IOException {
        PosixFileAttributeView posix=Files.getFileAttributeView(path,PosixFileAttributeView.class,LinkOption.NOFOLLOW_LINKS);
        if(posix!=null) { posix.setPermissions(PosixFilePermissions.fromString(directory?"rwx------":"rw-------"));return; }
        AclFileAttributeView acl=Files.getFileAttributeView(path,AclFileAttributeView.class,LinkOption.NOFOLLOW_LINKS);
        if(acl==null) throw new IOException("Private synthetic capability storage unavailable.");
        var entry=AclEntry.newBuilder().setType(AclEntryType.ALLOW).setPrincipal(Files.getOwner(path))
                .setPermissions(EnumSet.allOf(AclEntryPermission.class));
        if(directory) entry.setFlags(AclEntryFlag.FILE_INHERIT,AclEntryFlag.DIRECTORY_INHERIT);
        acl.setAcl(List.of(entry.build()));
    }
}
