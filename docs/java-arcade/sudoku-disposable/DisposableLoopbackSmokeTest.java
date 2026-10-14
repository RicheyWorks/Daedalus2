package com.xai.sudokupro;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.xai.sudokupro.model.SudokuBoard;
import com.xai.sudokupro.model.User;
import java.net.CookieManager;
import java.net.CookiePolicy;
import java.net.InetSocketAddress;
import java.net.Proxy;
import java.net.ProxySelector;
import java.net.Socket;
import java.net.SocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.WebSocket;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.function.Predicate;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.mockito.Answers;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.data.redis.RedisConnectionFailureException;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.connection.ReactiveRedisConnectionFactory;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.ActiveProfiles;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.exceptions.JedisConnectionException;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** Disposable-only test addition. The pinned application and rule sources stay unchanged. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
    "server.address=127.0.0.1",
    "spring.datasource.url=jdbc:h2:mem:disposable-arcade;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1",
    "spring.datasource.driver-class-name=org.h2.Driver",
    "spring.datasource.username=sa",
    "spring.datasource.password=",
    "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect",
    "spring.jpa.hibernate.ddl-auto=create-drop",
    "spring.flyway.enabled=false",
    "spring.security.user.name=fixture_admin",
    "spring.security.user.password=disposable_admin_fixture",
    "sudokupro.ui.enabled=false",
    "sudokupro.fcm.enabled=false",
    "sudokupro.fcm.service-account-file=",
    "sudokupro.chaos.enabled=false",
    "sudokupro.time-attack.seconds-per-level=1",
    "sudokupro.security.register.max-attempts=1000",
    "sudokupro.cache.shared=",
    "logging.level.root=WARN",
    "logging.level.com.xai.sudokupro=ERROR",
    "spring.main.banner-mode=off"
})
@ActiveProfiles("dev")
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
class DisposableLoopbackSmokeTest {
    static final String PIN = "973c73a35f8659a17022232f0996d4ffb0095997";
    static final String A = "fixture_arcade_a", B = "fixture_arcade_b";
    static final String FIXTURE_PASSWORD = "disposable_fixture_password";
    static final String NEW_FIXTURE_PASSWORD = "disposable_changed_fixture";
    final ObjectMapper json = new ObjectMapper();
    final List<Map<String,Object>> cases = new ArrayList<>();
    final List<WebSocket> sockets = new ArrayList<>();
    @LocalServerPort int port;
    @Autowired ConfigurableApplicationContext context;
    @MockBean(answer = Answers.RETURNS_SMART_NULLS) RedisConnectionFactory connectionFactory;
    @MockBean(answer = Answers.RETURNS_SMART_NULLS) ReactiveRedisConnectionFactory reactiveConnectionFactory;
    @MockBean(answer = Answers.RETURNS_SMART_NULLS) JedisPool jedisPool;
    @MockBean(name = "relayListenerContainer") RedisMessageListenerContainer relay;
    @MockBean(name = "stringRedisTemplate", answer = Answers.RETURNS_SMART_NULLS) StringRedisTemplate redis;
    @MockBean(name = "redisTemplate", answer = Answers.RETURNS_SMART_NULLS) RedisTemplate<String,User> userRedis;
    @MockBean(name = "gameStateRedisTemplate", answer = Answers.RETURNS_SMART_NULLS) RedisTemplate<String,SudokuBoard> gameRedis;

    static final ProxySelector DIRECT = new ProxySelector() {
        @Override public List<Proxy> select(URI uri) { return List.of(Proxy.NO_PROXY); }
        @Override public void connectFailed(URI uri, SocketAddress address, java.io.IOException failure) { }
    };

    HttpClient client() {
        return HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(4))
            .proxy(DIRECT).cookieHandler(new CookieManager(null, CookiePolicy.ACCEPT_ALL)).build();
    }
    String basic(String who, String password) {
        return "Basic " + Base64.getEncoder().encodeToString((who + ":" + password).getBytes(StandardCharsets.UTF_8));
    }
    HttpResponse<String> request(HttpClient client, String method, String path,
                                 String who, String password, String csrf, Object body) throws Exception {
        HttpRequest.Builder request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + path))
            .timeout(Duration.ofSeconds(8)).header("Accept","application/json");
        if (who != null) request.header("Authorization",basic(who,password));
        if (csrf != null) request.header("X-XSRF-TOKEN",csrf);
        if (body != null) request.header("Content-Type","application/json");
        request.method(method, body == null ? HttpRequest.BodyPublishers.noBody()
            : HttpRequest.BodyPublishers.ofString(json.writeValueAsString(body)));
        return client.send(request.build(), HttpResponse.BodyHandlers.ofString());
    }
    JsonNode document(HttpResponse<String> response, int expected, String label) throws Exception {
        assertEquals(expected,response.statusCode(),label + " HTTP status");
        return response.body().isBlank() ? null : json.readTree(response.body());
    }
    void record(String name) { cases.add(Map.of("case",name,"passed",true)); }
    void safeBoard(JsonNode board) {
        assertNotNull(board);
        assertEquals(9,board.path("cells").size());
        for (JsonNode row : board.path("cells")) assertEquals(9,row.size());
        String raw = board.toString().toLowerCase(java.util.Locale.ROOT);
        assertFalse(raw.contains("solution"));
        assertFalse(raw.contains("solvedgrid"));
        assertEquals(A,board.path("playerId").asText());
        assertTrue(board.has("timeLimitSeconds") && board.has("secondsLeft") && board.has("timeUp"));
    }
    JsonNode getBoard(HttpClient client, String id, String password) throws Exception {
        return document(request(client,"GET","/api/game/"+id,A,password,null,null),200,"read board");
    }
    WebSocket open(HttpClient client, String id, String who, String password, String ticket, Inbox inbox) throws Exception {
        URI uri = URI.create("ws://127.0.0.1:"+port+"/ws/game?gameId="+id+(ticket==null?"":"&ticket="+ticket));
        var builder=client.newWebSocketBuilder().connectTimeout(Duration.ofSeconds(5));
        if (who!=null) builder.header("Authorization",basic(who,password));
        WebSocket socket=builder.buildAsync(uri,inbox).get(8,TimeUnit.SECONDS);
        sockets.add(socket);
        return socket;
    }
    void send(WebSocket socket, String type, Object payload) throws Exception {
        socket.sendText(json.writeValueAsString(Map.of("type",type,"payload",payload)),true).get(4,TimeUnit.SECONDS);
    }
    JsonNode event(Inbox inbox, Predicate<JsonNode> match) throws Exception {
        long end=System.nanoTime()+TimeUnit.SECONDS.toNanos(8);
        while(System.nanoTime()<end) {
            String text=inbox.text.poll(200,TimeUnit.MILLISECONDS);
            if(text!=null) { JsonNode node=json.readTree(text); if(match.test(node))return node; }
        }
        fail("Expected socket event did not arrive within owned test deadline");
        return null;
    }
    JsonNode boardEvent(Inbox inbox) throws Exception {
        return event(inbox,node->"board".equals(node.path("type").asText())).path("payload");
    }
    int[][] visible(JsonNode board) {
        int[][] grid=new int[9][9];
        for(int r=0;r<9;r++)for(int c=0;c<9;c++)grid[r][c]=board.path("cells").get(r).get(c).path("value").asInt();
        return grid;
    }
    // Independent test oracle using only the visible puzzle; never a runtime rule port.
    boolean solve(int[][] grid) {
        for(int r=0;r<9;r++)for(int c=0;c<9;c++)if(grid[r][c]==0) {
            for(int value=1;value<=9;value++) {
                boolean legal=true;
                for(int i=0;i<9;i++)if(grid[r][i]==value||grid[i][c]==value)legal=false;
                for(int rr=r/3*3;rr<r/3*3+3;rr++)for(int cc=c/3*3;cc<c/3*3+3;cc++)
                    if(grid[rr][cc]==value)legal=false;
                if(legal) { grid[r][c]=value; if(solve(grid))return true; grid[r][c]=0; }
            }
            return false;
        }
        return true;
    }
    static class Inbox implements WebSocket.Listener {
        final BlockingQueue<String> text=new LinkedBlockingQueue<>();
        final CompletableFuture<Integer> closed=new CompletableFuture<>();
        final StringBuilder partial=new StringBuilder();
        @Override public void onOpen(WebSocket ws) { ws.request(1); }
        @Override public CompletionStage<?> onText(WebSocket ws,CharSequence data,boolean last) {
            partial.append(data); if(last){text.add(partial.toString());partial.setLength(0);}ws.request(1);return null;
        }
        @Override public CompletionStage<?> onClose(WebSocket ws,int code,String reason) {closed.complete(code);return null;}
        @Override public void onError(WebSocket ws,Throwable error) {closed.completeExceptionally(error);}
    }

    @Test @Timeout(120)
    @SuppressWarnings({"unchecked","rawtypes"})
    void realLoopbackHttpAndWebSocketWithSyntheticState() throws Exception {
        boolean success=false, stopped=false;
        Map<String,Object> proof=new LinkedHashMap<>();
        proof.put("sourceRepository","RicheyWorks/sudokupro"); proof.put("sourceCommit",PIN);
        proof.put("jvmPid",ProcessHandle.current().pid()); proof.put("loopbackPort",port);
        proof.put("startedAt",Instant.now().toString()); proof.put("runtimeVersion",Runtime.version().toString());
        proof.put("transport","Real JDK HTTP and WebSocket clients to embedded owned Tomcat");
        proof.put("isolation","dev SecurityConfig + H2 memory + Mockito Redis/Jedis/relay; synthetic accounts only");
        try {
            assertEquals("127.0.0.1",context.getEnvironment().getProperty("server.address"));
            assertEquals(java.util.Set.of("dev"),java.util.Set.of(context.getEnvironment().getActiveProfiles()));
            try(var connection=context.getBean(javax.sql.DataSource.class).getConnection()) {
                assertEquals("H2",connection.getMetaData().getDatabaseProductName());
                assertEquals("jdbc:h2:mem:disposable-arcade",connection.getMetaData().getURL());
                proof.put("effectiveDatasourceProduct","H2");
                proof.put("effectiveDatasourceUrl",connection.getMetaData().getURL());
            }
            var security=context.getBean(com.xai.sudokupro.config.SecurityConfig.class);
            assertFalse(mockingDetails(security).isMock());
            proof.put("realSecurityConfig",true);proof.put("activeProfiles",List.of("dev"));
            assertEquals("jdbc:h2:mem:disposable-arcade;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1",
                context.getEnvironment().getProperty("spring.datasource.url"));
            assertFalse(context.getEnvironment().getProperty("sudokupro.fcm.enabled",Boolean.class,true));
            for(Object mock:List.of(connectionFactory,reactiveConnectionFactory,jedisPool,relay,redis,userRedis,gameRedis))
                assertTrue(mockingDetails(mock).isMock(),"All Redis/Jedis/relay objects must be test mocks");
            proof.put("realRedisConnectionFactory",false); proof.put("realJedisPool",false);
            var down=new RedisConnectionFailureException("Disposable test: Redis intentionally unavailable");
            doThrow(down).when(connectionFactory).getConnection();
            doThrow(down).when(reactiveConnectionFactory).getReactiveConnection();
            doThrow(new JedisConnectionException("Disposable test only")).when(jedisPool).getResource();
            doThrow(down).when(redis).opsForValue(); doThrow(down).when(redis).opsForSet();
            doThrow(down).when(redis).opsForZSet(); doThrow(down).when(redis).opsForHash();
            doThrow(down).when(userRedis).opsForValue(); doThrow(down).when(gameRedis).opsForValue();
            when(redis.execute(any(RedisScript.class),anyList(),any(Object[].class))).thenThrow(down);
            when(redis.execute(any(RedisCallback.class))).thenThrow(down);
            record("isolated_h2_real_security_all_redis_mocked");

            HttpClient anonymous=client(), alice=client(), bob=client();
            assertEquals(401,request(anonymous,"GET","/api/session",null,null,null,null).statusCode());
            record("anonymous_http_session_401");
            for(String who:List.of(A,B))document(request(anonymous,"POST","/api/auth/register",null,null,null,
                Map.of("username",who,"password",FIXTURE_PASSWORD)),201,"synthetic registration");
            record("two_synthetic_accounts_registered");
            assertEquals(401,request(client(),"GET","/api/session",A,"wrong_fixture_password",null,null).statusCode());
            record("wrong_basic_credentials_401");

            JsonNode session=document(request(alice,"GET","/api/session",A,FIXTURE_PASSWORD,null,null),200,"bootstrap");
            assertEquals(A,session.path("playerId").asText());
            assertEquals("X-XSRF-TOKEN",session.path("csrfHeaderName").asText());
            assertFalse(session.path("csrfToken").asText().isEmpty());
            assertFalse(session.path("wsTicket").asText().isEmpty());
            String csrf=session.path("csrfToken").asText();
            record("real_basic_csrf_cookie_header_bootstrap");
            assertEquals(403,request(alice,"POST","/api/game/new?difficulty=1",A,FIXTURE_PASSWORD,null,null).statusCode());
            record("mutation_missing_csrf_403");
            JsonNode board=document(request(alice,"POST","/api/game/new?difficulty=1&chaos=false&mirror=false&timeAttack=false",
                A,FIXTURE_PASSWORD,csrf,null),200,"new");
            safeBoard(board);String id=board.path("gameId").asText();assertFalse(id.isEmpty());
            record("new_own_game_direct_visible_81_cell_snapshot");
            safeBoard(getBoard(alice,id,FIXTURE_PASSWORD));record("read_board_no_hidden_solution");

            JsonNode bobSession=document(request(bob,"GET","/api/session",B,FIXTURE_PASSWORD,null,null),200,"bob bootstrap");
            String bobCsrf=bobSession.path("csrfToken").asText();
            assertEquals(200,request(bob,"GET","/api/game/"+id,B,FIXTURE_PASSWORD,null,null).statusCode());
            record("authenticated_free_play_spectator_read_allowed");
            assertEquals(403,request(bob,"POST","/api/game/"+id+"/save",B,FIXTURE_PASSWORD,bobCsrf,null).statusCode());
            record("other_owner_save_403");
            assertEquals(403,request(bob,"POST","/api/game/hint?gameId="+id,B,FIXTURE_PASSWORD,bobCsrf,null).statusCode());
            record("other_owner_hint_403");

            Inbox unauthenticated=new Inbox();open(client(),id,null,null,null,unauthenticated);
            assertEquals(1008,unauthenticated.closed.get(8,TimeUnit.SECONDS));
            record("anonymous_websocket_closed_1008");
            Inbox owner=new Inbox();WebSocket ownerSocket=open(alice,id,A,FIXTURE_PASSWORD,null,owner);
            send(ownerSocket,"sync","");safeBoard(boardEvent(owner));record("jdk_basic_socket_full_sync");

            int row=-1,col=-1,givenRow=-1,givenCol=-1;
            int[][] solution=visible(board);assertTrue(solve(solution),"Independent visible-puzzle test oracle");
            for(int r=0;r<9;r++)for(int c=0;c<9;c++) {
                JsonNode cell=board.path("cells").get(r).get(c);
                if(row<0&&cell.path("value").asInt()==0){row=r;col=c;}
                if(givenRow<0&&cell.path("isGiven").asBoolean()){givenRow=r;givenCol=c;}
            }
            assertTrue(row>=0&&givenRow>=0);
            final int rr=row,cc=col,value=solution[row][col];
            send(ownerSocket,"move",Map.of("row",row,"col",col,"oldVal",0,"newVal",value,"source","AUTOSOLVE"));
            JsonNode echo=event(owner,node->"move".equals(node.path("type").asText())
                &&node.path("payload").path("row").asInt()==rr&&node.path("payload").path("col").asInt()==cc);
            assertEquals("PLAYER",echo.path("payload").path("source").asText());
            assertEquals(value,getBoard(alice,id,FIXTURE_PASSWORD).path("cells").get(row).get(col).path("value").asInt());
            record("socket_move_accepted_and_spoofed_source_stamped_player");
            send(ownerSocket,"undo","");JsonNode undone=boardEvent(owner);
            assertEquals(0,undone.path("cells").get(row).get(col).path("value").asInt());
            record("socket_undo_full_authoritative_board");
            send(ownerSocket,"redo","");JsonNode redone=boardEvent(owner);
            assertEquals(value,redone.path("cells").get(row).get(col).path("value").asInt());
            assertFalse(redone.path("cells").get(row).get(col).path("isEditable").asBoolean());
            assertFalse(redone.path("cells").get(row).get(col).path("isGiven").asBoolean());
            record("socket_redo_filled_player_cell_view_flags");
            send(ownerSocket,"move",Map.of("row",row,"col",col,"oldVal",value,"newVal",0));
            event(owner,node->"move".equals(node.path("type").asText())&&node.path("payload").path("newVal").asInt()==0);
            assertEquals(0,getBoard(alice,id,FIXTURE_PASSWORD).path("cells").get(row).get(col).path("value").asInt());
            record("filled_non_given_can_be_erased");
            send(ownerSocket,"move",Map.of("row",givenRow,"col",givenCol,"oldVal",solution[givenRow][givenCol],"newVal",0));
            assertEquals("Invalid move",event(owner,node->"error".equals(node.path("type").asText())).path("payload").path("detail").asText());
            record("given_cell_erase_refused_by_java");

            Inbox spectator=new Inbox();WebSocket spectatorSocket=open(bob,id,B,FIXTURE_PASSWORD,null,spectator);
            send(spectatorSocket,"move",Map.of("row",row,"col",col,"oldVal",0,"newVal",value));
            assertTrue(event(spectator,node->"error".equals(node.path("type").asText())).path("payload").path("detail").asText().contains("Spectators cannot modify"));
            record("spectator_socket_mutation_refused");

            JsonNode wallet=document(request(alice,"GET","/api/economy/wallet",A,FIXTURE_PASSWORD,null,null),200,"wallet");
            int beforeGems=wallet.path("gems").asInt(),cost=wallet.path("hintCost").asInt();
            int beforeHints=getBoard(alice,id,FIXTURE_PASSWORD).path("hintCount").asInt();
            JsonNode hint=document(request(alice,"POST","/api/game/hint?gameId="+id,A,FIXTURE_PASSWORD,csrf,null),200,"hint");
            assertTrue(hint.has("hint"));
            JsonNode afterHint=getBoard(alice,id,FIXTURE_PASSWORD);
            JsonNode afterWallet=document(request(alice,"GET","/api/economy/wallet",A,FIXTURE_PASSWORD,null,null),200,"wallet after hint");
            int hintsDelta=afterHint.path("hintCount").asInt()-beforeHints;
            assertEquals(hintsDelta>0?cost:0,beforeGems-afterWallet.path("gems").asInt());
            proof.put("hintCountDelta",hintsDelta);proof.put("hintGemDelta",beforeGems-afterWallet.path("gems").asInt());
            record("hint_response_and_actual_virtual_gem_charge");
            JsonNode saved=document(request(alice,"POST","/api/game/"+id+"/save",A,FIXTURE_PASSWORD,csrf,null),200,"save");
            assertEquals("saved",saved.path("status").asText());assertEquals(id,saved.path("gameId").asText());
            JsonNode savedList=document(request(alice,"GET","/api/game/saved?limit=10",A,FIXTURE_PASSWORD,null,null),200,"saved list");
            boolean found=false;for(JsonNode entry:savedList)if(id.equals(entry.path("gameId").asText()))found=true;
            assertTrue(found);record("explicit_save_and_own_saved_list");
            JsonNode resumed=document(request(alice,"POST","/api/game/"+id+"/resume",A,FIXTURE_PASSWORD,csrf,null),200,"resume");
            safeBoard(resumed);assertEquals(afterHint.path("hintCount").asInt(),resumed.path("hintCount").asInt());
            record("resume_own_board_and_persisted_hint_counter");

            String ticket=bobSession.path("wsTicket").asText();Inbox ticketInbox=new Inbox();
            WebSocket ticketSocket=open(bob,id,null,null,ticket,ticketInbox);
            send(ticketSocket,"sync","");assertEquals(id,boardEvent(ticketInbox).path("gameId").asText());
            record("single_use_ticket_socket_authentication");
            Inbox reusedTicket=new Inbox();open(bob,id,null,null,ticket,reusedTicket);
            assertEquals(1008,reusedTicket.closed.get(8,TimeUnit.SECONDS));
            record("reused_ticket_socket_closed_1008_despite_valid_cookie");

            JsonNode daily=document(request(alice,"POST","/api/daily/join",A,FIXTURE_PASSWORD,csrf,null),200,"daily");
            Inbox rejectedCompetitive=new Inbox();open(bob,daily.path("gameId").asText(),B,FIXTURE_PASSWORD,null,rejectedCompetitive);
            assertEquals(1008,rejectedCompetitive.closed.get(8,TimeUnit.SECONDS));
            record("other_player_competitive_socket_join_refused");

            JsonNode timed=document(request(alice,"POST","/api/game/new?difficulty=1&timeAttack=true",A,FIXTURE_PASSWORD,csrf,null),200,"timed");
            String timedId=timed.path("gameId").asText();assertEquals(1,timed.path("timeLimitSeconds").asLong());
            Thread.sleep(1600);
            JsonNode expired=getBoard(alice,timedId,FIXTURE_PASSWORD);assertTrue(expired.path("timeUp").asBoolean());
            JsonNode expiredHint=document(request(alice,"POST","/api/game/hint?gameId="+timedId,A,FIXTURE_PASSWORD,csrf,null),409,"expired hint");
            assertEquals("Time's Up",expiredHint.path("title").asText());
            record("server_clock_time_attack_and_expired_hint_409");

            document(request(alice,"POST","/api/auth/password",A,FIXTURE_PASSWORD,csrf,
                Map.of("currentPassword",FIXTURE_PASSWORD,"newPassword",NEW_FIXTURE_PASSWORD)),200,"synthetic password change");
            assertEquals(1008,owner.closed.get(8,TimeUnit.SECONDS));
            assertEquals(401,request(client(),"GET","/api/session",A,FIXTURE_PASSWORD,null,null).statusCode());
            assertEquals(200,request(client(),"GET","/api/session",A,NEW_FIXTURE_PASSWORD,null,null).statusCode());
            record("synthetic_password_revokes_old_http_and_existing_socket");
            success=true;
        } finally {
            for(WebSocket socket:sockets)try {socket.sendClose(1000,"Disposable check complete").get(2,TimeUnit.SECONDS);}
                catch(Exception ignored){socket.abort();}
            // Stop owned listener now; Spring closes beans safely after test callbacks.
            context.stop();
            try(Socket probe=new Socket()) {
                probe.connect(new InetSocketAddress("127.0.0.1",port),500);
                stopped=false;
            } catch(java.io.IOException expected){stopped=true;}
            proof.put("passed",success);proof.put("cases",cases);proof.put("caseCount",cases.size());
            proof.put("ownedListenerStopped",stopped);proof.put("finishedAt",Instant.now().toString());
            proof.put("notProven",List.of("Real Redis/PostgreSQL","Redis scripts or cross-replica behavior",
                "Unreal native parser/transport","Plugin load or packaged/in-world acceptance"));
            Files.writeString(Path.of("../disposable-evidence.json"),json.writerWithDefaultPrettyPrinter().writeValueAsString(proof)+"\n");
            assertTrue(stopped,"Owned loopback listener must stop");
        }
    }
}
