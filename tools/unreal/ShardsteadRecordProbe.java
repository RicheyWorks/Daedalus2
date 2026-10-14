import com.daedalus.world.persistence.RealmRecordStore;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

/** Disposable native payload/storage interoperability probe; never opens a live realm store. */
public final class ShardsteadRecordProbe {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("input native payload, returned output path");
        Path input = Path.of(args[0]), output = Path.of(args[1]);
        if (Files.exists(output)) throw new IllegalArgumentException("Output must be fresh");
        Path directory = Files.createTempDirectory(output.toAbsolutePath().getParent(), "shardstead-record-");
        byte[] payload = Files.readAllBytes(input);
        try (var store = new RealmRecordStore(directory)) {
            if (store.compareAndSet("WORLD-ZERO", "shardstead-ledger", 0, payload).result() != RealmRecordStore.WriteResult.UPDATED)
                throw new AssertionError("initial storage write");
            if (store.compareAndSet("WORLD-ZERO", "shardstead-ledger", 0, payload).result() != RealmRecordStore.WriteResult.REPLAY)
                throw new AssertionError("storage replay");
            if (store.compareAndSet("WORLD-ZERO", "shardstead-ledger", 0, new byte[] {1}).result() != RealmRecordStore.WriteResult.CONFLICT)
                throw new AssertionError("conflicting storage write");
        }
        try (var reopened = new RealmRecordStore(directory)) {
            var record = reopened.read("WORLD-ZERO", "shardstead-ledger").orElseThrow();
            if (record.revision() != 1 || !Arrays.equals(payload, record.payload())) throw new AssertionError("reopen mismatch");
            Files.write(output, record.payload());
        }
        System.out.println("PASS native bytes persisted/replayed/conflict-checked and reopened: " + directory);
    }
}
