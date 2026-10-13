// SPDX-License-Identifier: MIT
import com.daedalus.world.Chunk;
import com.daedalus.world.BlockType;

/** Adversarial storage scenarios, not a terrain generation or player capacity benchmark. */
public class ChunkSizingProbe {
    public static void main(String[] args) {
        System.out.println("scenario,bits,chunk_storage_estimate,chunk_runs,land_storage_estimate,land_runs");
        for(int mode=0;mode<3;mode++) {
            Chunk chunk=new Chunk();var kinds=BlockType.values();
            for(int z=0;z<16;z++) for(int y=0;y<16;y++) for(int x=0;x<16;x++) {
                int index=x+16*(y+16*z);
                chunk.set(x,y,z,kinds[mode==0?1:mode==1?(y<8?1:2):index%17]);
            }
            chunk=chunk.compacted();long storage=chunk.storageBytes(),runs=chunk.runs().length;
            System.out.println(new String[]{"uniform","layered","fragmented17"}[mode]+","+chunk.bitsPerBlock()+","+storage+","+runs+","+storage*2048+","+runs*2048);
        }
    }
}
