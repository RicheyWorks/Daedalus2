// SPDX-License-Identifier: MIT
import com.daedalus.world.*;
import com.daedalus.world.ocean.OceanTerrain;
import com.daedalus.world.export.Glb;
import com.daedalus.world.export.WorldMesher;
import java.nio.file.*;
import java.util.ArrayList;

/** Run with Java 21 source-file mode and daedalus-core/target/classes on the classpath. */
class OceanBootstrap {
    public static void main(String[] args) throws Exception {
        if(args.length!=2)throw new IllegalArgumentException("OceanBootstrap FRESH_DIRECTORY SEED");
        Path output=Path.of(args[0]).toAbsolutePath();long seed=Long.parseLong(args[1]);
        Files.createDirectory(output); // Existing deliveries are never replaced.
        long start=System.nanoTime();
        var requested=new ArrayList<ChunkCoordinate>();
        for(int x=-2;x<=1;x++)for(int y=-3;y<=0;y++)for(int z=-2;z<=1;z++)requested.add(new ChunkCoordinate(x,y,z));
        World world=OceanTerrain.newWorld(new WorldId("ocean"),seed,requested);
        WorldStore.save(world,output.resolve("ocean.daew"));
        World loaded=WorldStore.load(output.resolve("ocean.daew"));
        for(var at:world.chunkKeys())if(!world.chunk(at).equals(loaded.chunk(at)))throw new IllegalStateException("Save round trip mismatch");
        var meshes=WorldMesher.mesh(loaded);
        byte[] glb=Glb.write(meshes,"Daedalus OceanTerrain v"+OceanTerrain.VERSION);
        Files.write(output.resolve("ocean.glb"),glb,StandardOpenOption.CREATE_NEW);
        long faces=meshes.stream().mapToLong(m->m.opaque().faceCount()+m.translucent().faceCount()).sum();
        String metadata=String.format(java.util.Locale.ROOT,"""
                {
                  "realm": "ocean", "generator_version": %d, "seed": %d,
                  "requested_chunks": %d, "stored_chunks": %d, "triangles": %d,
                  "units": "metres", "up_axis": "Y",
                  "bounds": {"min": [-32,-48,-32], "max_exclusive": [32,16,32]},
                  "spawn": [0,2,0], "boat_berth": [0,1,8], "submarine_berth": [0,-8,8],
                  "server_registered": false, "unreal_play_verified": false,
                  "generation_save_reload_mesh_seconds": %.6f
                }
                """,OceanTerrain.VERSION,seed,requested.size(),loaded.chunkCount(),faces*2,(System.nanoTime()-start)/1e9);
        Files.writeString(output.resolve("ocean.json"),metadata,StandardOpenOption.CREATE_NEW);
        System.out.println(metadata);
    }
}
