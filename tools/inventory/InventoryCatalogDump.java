import com.daedalus.world.inventory.InventoryCatalog;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HexFormat;

/** Test adapter for exact native/Java catalog parity; not a server endpoint. */
public class InventoryCatalogDump {
    private static String hex(String value) {
        return HexFormat.of().formatHex(value.getBytes(StandardCharsets.UTF_8));
    }
    public static void main(String[] args) throws Exception {
        var catalog = InventoryCatalog.parse(Files.readString(Path.of(args[0])));
        System.out.println("realm\t" + hex(catalog.realm()));
        System.out.println("theme\t" + hex(catalog.theme()));
        for (var tab : catalog.tabs()) System.out.println("tab\t" + hex(tab));
        for (var slot : catalog.slots()) System.out.println("slot\t" + hex(slot));
        for (var item : catalog.items()) {
            System.out.print("item\t" + hex(item.id()) + "\t" + hex(item.tab()) + "\t" + hex(item.slot())
                    + "\t" + hex(item.name()) + "\t" + hex(item.detail()));
            for (var action : item.actions()) System.out.print("\t" + hex(action));
            System.out.println();
        }
    }
}
