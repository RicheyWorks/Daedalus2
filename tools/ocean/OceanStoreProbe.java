// SPDX-License-Identifier: MIT
import com.daedalus.world.*;
import com.daedalus.world.ocean.OceanChunkStore;
import com.daedalus.world.ocean.OceanChunkWindow;
import java.io.IOException;
import java.nio.file.Path;

/** Separate-JVM restart/OS-lock probe, used by ocean-store CI. */
class OceanStoreProbe {
    public static void main(String[] args) throws Exception {
        if(args.length!=2)throw new IllegalArgumentException("OceanStoreProbe MODE DIRECTORY");
        Path root=Path.of(args[1]);
        if(args[0].startsWith("window-")) {
            try(var window=new OceanChunkWindow(root,42,3)) {
                var edited=new BlockCoordinate(-1,-1,-1);
                if(args[0].equals("window-write")) {
                    window.set(edited,BlockType.WOOD);
                    for(int x=0;x<20;x++) {
                        window.get(new BlockCoordinate(x*16,-1,0));
                        if(window.residentCount()>3)throw new IllegalStateException("Resident cap exceeded");
                    }
                    if(window.get(edited)!=BlockType.WOOD)throw new IllegalStateException("Edit lost on eviction");
                    System.out.println("OCEAN_WINDOW_WRITE_PASS");
                } else if(args[0].equals("window-read")) {
                    if(window.get(edited)!=BlockType.WOOD)throw new IllegalStateException("Edit lost on process restart");
                    System.out.println("OCEAN_WINDOW_RESTART_PASS");
                } else throw new IllegalArgumentException("Unknown window probe");
            }
            return;
        }
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
                    Chunk clear=store.loadOrGenerate(emptied);
                    for(int x=0;x<16;x++)for(int y=0;y<16;y++)for(int z=0;z<16;z++)clear.set(x,y,z,BlockType.AIR);
                    store.save(emptied,clear);
                    System.out.println("OCEAN_PROCESS_WRITE_PASS");
                }
                case "read" -> {
                    if(store.loadOrGenerate(edited).get(1,2,3)!=BlockType.GLASS||!store.loadOrGenerate(emptied).isEmpty()
                            ||store.loadOrGenerate(emptied).revision()<=4096) {
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
