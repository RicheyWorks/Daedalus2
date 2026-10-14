// SPDX-License-Identifier: MIT
// Run with Java 21 and daedalus-core/target/classes on the class path.
import com.daedalus.world.World;
import com.daedalus.world.WorldId;
import com.daedalus.world.WorldStore;
import com.daedalus.world.export.Glb;
import com.daedalus.world.export.WorldMesher;
import com.daedalus.world.labyrinth.LabyrinthTerrain;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;

class ExportLabyrinth {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("output directory and signed long seed required");
        Path directory = Path.of(args[0]);
        Files.createDirectories(directory);
        Path glb = directory.resolve("Labyrinth_Starter.glb");
        Path volume = directory.resolve("labyrinth.daew");
        Path manifest = directory.resolve("labyrinth-starter.json");
        for (Path path : new Path[]{glb, volume, manifest}) {
            if (Files.exists(path)) throw new IllegalArgumentException("Refusing to replace " + path);
        }
        long seed = Long.parseLong(args[1]);
        World world = new World(new WorldId("labyrinth"));
        if (!LabyrinthTerrain.build(world, seed).ok()) throw new IllegalStateException("Build refused");
        byte[] bytes = Glb.write(WorldMesher.meshGreedy(world), "Daedalus Labyrinth starter");
        Files.write(glb, bytes);
        WorldStore.save(world, volume);
        String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        var spawn = LabyrinthTerrain.spawn();
        var exit = LabyrinthTerrain.exit();
        Files.writeString(manifest, """
                {
                  "schema": 1,
                  "realm": "LABYRINTH",
                  "scope": "bounded starter terrain; not the complete realm",
                  "seed": "%s",
                  "sideMetres": %d,
                  "corridorWidthMetres": %d,
                  "coordinates": "glTF right-handed Y-up metres; feet anchors",
                  "spawn": [%d, %d, %d],
                  "exit": [%d, %d, %d],
                  "chunks": %d,
                  "glbBytes": %d,
                  "glbSha256": "%s",
                  "unrealImportAndCollisionVerified": false
                }
                """.formatted(seed, LabyrinthTerrain.SIDE, LabyrinthTerrain.SCALE,
                    spawn.x(), spawn.y(), spawn.z(), exit.x(), exit.y(), exit.z(),
                    world.chunkCount(), bytes.length, hash));
        System.out.println(manifest.toAbsolutePath());
        System.out.println(hash + " " + bytes.length + " bytes");
    }
}
