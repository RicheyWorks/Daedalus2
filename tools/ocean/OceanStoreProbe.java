// SPDX-License-Identifier: MIT
import com.daedalus.world.*;
import com.daedalus.world.ocean.OceanChunkStore;
import java.io.IOException;
import java.nio.file.Path;

/** Separate-JVM restart/OS-lock probe, used by ocean-store CI. */
class OceanStoreProbe {
    public static void main(String[] args) throws Exception {
        if(args.length!=2)throw new IllegalArgumentException("OceanStoreProbe MODE DIRECTORY");
        Path root=Path.of(args[1]);
        if(args[0].equals("locked")) {
            try(var unexpected=new OceanChunkStore(root,42)) {
                throw new IllegalStateException("Concurrent writer unexpectedly acquired lock");
            } catch(IOException expected) {
                if(!expected.getMessage().contains("owned"))throw expected;
                System.out.println("OCEAN_OS_LOCK_REFUSED");return;
            }
        }
        try(var store=new OceanChunkStore(root,42)) {
            var edited=new ChunkCoordinate(0,-1,0);var emptied=new ChunkCoordinate(1,-1,0);
            switch(args[0]) {
                case "write" -> {
                    Chunk chunk=store.loadOrGenerate(edited);chunk.set(1,2,3,BlockType.GLASS);store.save(edited,chunk);
                    store.loadOrGenerate(emptied);store.save(emptied,new Chunk());
                    System.out.println("OCEAN_PROCESS_WRITE_PASS");
                }
                case "read" -> {
                    if(store.loadOrGenerate(edited).get(1,2,3)!=BlockType.GLASS||!store.loadOrGenerate(emptied).isEmpty()) {
                        throw new IllegalStateException("Persisted edit/empty chunk lost");
                    }
                    System.out.println("OCEAN_PROCESS_RESTART_PASS");
                }
                case "hold" -> {System.out.println("OCEAN_LOCK_READY");System.out.flush();System.in.read();}
                default -> throw new IllegalArgumentException("Unknown probe mode");
            }
        }
    }
}
