package com.daedalus.world.inventory;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Immutable reader for Claude's DIC 1 catalogs. Does not mutate player inventory. */
public record InventoryCatalog(String realm, String theme, List<String> tabs,
                               List<String> slots, List<Item> items) {
    public InventoryCatalog {
        tabs = List.copyOf(tabs);
        slots = List.copyOf(slots);
        items = List.copyOf(items);
    }

    public record Item(String id, String tab, String slot, List<String> actions,
                       String name, String detail) {
        public Item { actions = List.copyOf(actions); }
    }

    public static InventoryCatalog parse(String text) {
        String[] lines = text.replace("\r", "").split("\n", -1);
        if (!lines[0].equals("DIC 1")) throw error(1, "expected DIC 1");
        String realm = "", theme = "default";
        List<String> tabs = new ArrayList<>(), slots = new ArrayList<>();
        Map<String, Item> items = new LinkedHashMap<>();
        for (int i = 1; i < lines.length; i++) {
            String line = lines[i];
            if (line.isEmpty() || line.startsWith("#")) continue;
            List<String> f = Arrays.stream(line.split(" ")).filter(s -> !s.isEmpty()).toList();
            if (f.isEmpty()) throw error(i + 1, "empty record");
            int n = i + 1;
            switch (f.getFirst()) {
                case "realm" -> {
                    if (f.size() < 2) throw error(n, "realm needs a name");
                    realm = rest(f, 1);
                }
                case "theme" -> {
                    if (f.size() != 2) throw error(n, "theme needs one name");
                    theme = f.get(1);
                }
                case "tab", "slot" -> {
                    if (f.size() != 2 || !id(f.get(1))) throw error(n, "invalid tab/slot");
                    List<String> target = f.getFirst().equals("tab") ? tabs : slots;
                    if (target.contains(f.get(1))) throw error(n, "duplicate tab/slot");
                    if (target == tabs && tabs.size() >= 12) throw error(n, "too many tabs");
                    target.add(f.get(1));
                }
                case "item" -> {
                    if (f.size() < 6 || !id(f.get(1))) throw error(n, "invalid item");
                    String key = f.get(1), tab = f.get(2), slot = f.get(3).equals("-") ? "" : f.get(3);
                    if (items.containsKey(key) || !tabs.contains(tab) || tab.equals("ALL"))
                        throw error(n, "duplicate item or unknown item tab");
                    if (!slot.isEmpty() && !slots.contains(slot)) throw error(n, "unknown item slot");
                    List<String> actions = Arrays.stream(f.get(4).split(",")).filter(s -> !s.isEmpty()).toList();
                    if (actions.stream().anyMatch(a -> !id(a)) || (actions.contains("EQUIP") && slot.isEmpty()))
                        throw error(n, "invalid action or EQUIP without slot");
                    items.put(key, new Item(key, tab, slot, actions, rest(f, 5), ""));
                }
                case "detail" -> {
                    if (f.size() < 3 || !items.containsKey(f.get(1))) throw error(n, "unknown detail item");
                    Item old = items.get(f.get(1));
                    items.put(old.id(), new Item(old.id(), old.tab(), old.slot(), old.actions(), old.name(), rest(f, 2)));
                }
                default -> throw error(n, "unknown record");
            }
        }
        if (realm.isEmpty() || tabs.isEmpty()) throw error(lines.length, "realm and tabs required");
        return new InventoryCatalog(realm, theme, tabs, slots, new ArrayList<>(items.values()));
    }

    private static boolean id(String s) { return s.matches("[A-Za-z0-9_-]{1,48}"); }
    private static String rest(List<String> f, int start) { return String.join(" ", f.subList(start, f.size())); }
    private static IllegalArgumentException error(int line, String message) {
        return new IllegalArgumentException("line " + line + ": " + message);
    }
}
