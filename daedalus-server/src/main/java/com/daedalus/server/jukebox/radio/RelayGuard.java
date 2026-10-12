// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox.radio;

import java.net.Inet4Address;
import java.net.Inet6Address;
import java.net.InetAddress;
import java.net.URI;
import java.net.UnknownHostException;
import java.util.Locale;

/**
 * Keeps the radio relay from becoming an SSRF / open proxy. A URL may be fetched only if it is http(s), has no user
 * info, uses port 80, 443 or an unprivileged port (1024+), and every address its host resolves to is public:
 * no loopback, unspecified, link-local (cloud metadata), site-local / RFC 1918, CGNAT, unique-local IPv6,
 * multicast, benchmarking, documentation or reserved ranges, and no IPv4-mapped/compatible/6to4/NAT64 wrapping of those.
 * The relay checks this on the station URL and again on every redirect hop (redirects are followed by hand, at most
 * {@link #MAX_REDIRECTS}). Only stations this server listed are ever relayed in the first place.
 */
public final class RelayGuard implements UrlCheck {

    public static final int MAX_REDIRECTS = 3;

    /** Pluggable DNS so tests can resolve hostnames to chosen addresses. */
    @FunctionalInterface
    public interface Resolver { InetAddress[] resolve(String host) throws UnknownHostException; }

    private final Resolver dns;
    private final java.util.List<int[]> fakeIpRanges;     // {network, maskBits} (IPv4)

    public RelayGuard() {
        this(InetAddress::getAllByName);
    }

    public RelayGuard(Resolver dns) {
        this(dns, "");
    }

    /**
     * {@code fakeIpCidrs}: opt-in, default empty. Some sandboxes and corporate egress proxies answer DNS for every
     * public host with a "fake IP" (for example 198.18.0.0/15) and proxy the real connection. Listing such a range lets
     * a DNS name that resolves into it through. An IP literal in that range is still refused, so a station URL can
     * never name the proxy itself.
     */
    public RelayGuard(Resolver dns, String fakeIpCidrs) {
        this.dns = dns;
        this.fakeIpRanges = parseCidrs(fakeIpCidrs);
    }

    static java.util.List<int[]> parseCidrs(String csv) {
        java.util.List<int[]> out = new java.util.ArrayList<>();
        if (csv == null || csv.isBlank()) return out;
        for (String c : csv.split(",")) {
            String[] p = c.trim().split("/");
            if (p.length != 2 || !p[0].matches("\\d{1,3}(\\.\\d{1,3}){3}")) throw new IllegalArgumentException("not an IPv4 CIDR: " + c);
            int bits = Integer.parseInt(p[1]);
            if (bits < 8 || bits > 32) throw new IllegalArgumentException("CIDR too wide: " + c);
            int net = 0;
            for (String o : p[0].split("\\.")) {
                int v = Integer.parseInt(o);
                if (v > 255) throw new IllegalArgumentException("not an IPv4 CIDR: " + c);
                net = (net << 8) | v;
            }
            out.add(new int[]{net, bits});
        }
        return java.util.List.copyOf(out);
    }

    private boolean inFakeIpRange(InetAddress a) {
        byte[] b = a.getAddress();
        if (b.length != 4) return false;
        int ip = ((b[0] & 255) << 24) | ((b[1] & 255) << 16) | ((b[2] & 255) << 8) | (b[3] & 255);
        for (int[] r : fakeIpRanges) {
            int mask = r[1] == 32 ? -1 : ~(-1 >>> r[1]);
            if ((ip & mask) == (r[0] & mask)) return true;
        }
        return false;
    }

    private static boolean isIpLiteral(String h) {
        return h.contains(":") || h.matches("\\d{1,3}(\\.\\d{1,3}){3}");
    }

    /** Throws {@link Refused} unless {@code url} is safe to fetch. Returns the parsed URI. */
    @Override
    public URI check(String url) {
        URI u;
        try {
            u = URI.create(url.trim());
        } catch (IllegalArgumentException | NullPointerException e) {
            throw new Refused("not a URL");
        }
        String scheme = u.getScheme() == null ? "" : u.getScheme().toLowerCase(Locale.ROOT);
        if (!scheme.equals("http") && !scheme.equals("https")) throw new Refused("scheme " + scheme);
        if (u.getRawUserInfo() != null) throw new Refused("user info in URL");
        String host = u.getHost();
        if (host == null || host.isEmpty()) throw new Refused("no host");
        int port = u.getPort();
        if (port != -1 && port != 80 && port != 443 && (port < 1024 || port > 65535)) throw new Refused("port " + port);
        String h = host.startsWith("[") ? host.substring(1, host.length() - 1) : host;
        if (h.equalsIgnoreCase("localhost") || h.toLowerCase(Locale.ROOT).endsWith(".localhost")
                || h.toLowerCase(Locale.ROOT).endsWith(".internal") || h.toLowerCase(Locale.ROOT).endsWith(".local"))
            throw new Refused("local host name");
        InetAddress[] all;
        try {
            all = dns.resolve(h);
        } catch (UnknownHostException e) {
            throw new Refused("unknown host");
        }
        if (all == null || all.length == 0) throw new Refused("unknown host");
        boolean name = !isIpLiteral(h);
        for (InetAddress a : all)
            if (!isPublic(a) && !(name && inFakeIpRange(a))) throw new Refused("non-public address " + a.getHostAddress());
        return u;
    }

    /** True only for globally routable unicast addresses. */
    public static boolean isPublic(InetAddress a) {
        if (a.isAnyLocalAddress() || a.isLoopbackAddress() || a.isLinkLocalAddress() || a.isSiteLocalAddress()
                || a.isMulticastAddress()) return false;
        byte[] b = a.getAddress();
        if (a instanceof Inet4Address) return isPublicV4(b);
        if (a instanceof Inet6Address) {
            int b0 = b[0] & 0xff, b1 = b[1] & 0xff;
            if ((b0 & 0xfe) == 0xfc) return false;                         // fc00::/7 unique local
            if (b0 == 0xfe && (b1 & 0xc0) == 0xc0) return false;          // fec0::/10 site local (old)
            if (b0 == 0x20 && b1 == 0x01 && (b[2] & 0xff) == 0x0d && (b[3] & 0xff) == 0xb8) return false;   // 2001:db8::/32 docs
            if (b0 == 0x20 && b1 == 0x02) return isPublicV4(new byte[]{b[2], b[3], b[4], b[5]});            // 6to4 wraps v4
            if (b0 == 0x00 && b1 == 0x64 && (b[2] & 0xff) == 0xff && (b[3] & 0xff) == 0x9b)                 // 64:ff9b::/96 NAT64
                return isPublicV4(new byte[]{b[12], b[13], b[14], b[15]});
            boolean zero10 = true;
            for (int i = 0; i < 10; i++) zero10 &= b[i] == 0;
            if (zero10 && b[10] == 0 && b[11] == 0) return false;                                          // ::/96 v4-compatible
            if (zero10 && (b[10] & 0xff) == 0xff && (b[11] & 0xff) == 0xff)                                 // ::ffff:0:0/96 mapped
                return isPublicV4(new byte[]{b[12], b[13], b[14], b[15]});
            return (b0 & 0xe0) == 0x20;                                   // only 2000::/3 is global unicast
        }
        return false;
    }

    private static boolean isPublicV4(byte[] b) {
        int a0 = b[0] & 0xff, a1 = b[1] & 0xff, a2 = b[2] & 0xff;
        if (a0 == 0 || a0 == 10 || a0 == 127 || a0 >= 224) return false;            // this-net, private, loopback, multicast+reserved
        if (a0 == 100 && a1 >= 64 && a1 <= 127) return false;                        // 100.64/10 CGNAT
        if (a0 == 169 && a1 == 254) return false;                                    // link local / metadata
        if (a0 == 172 && a1 >= 16 && a1 <= 31) return false;
        if (a0 == 192 && a1 == 168) return false;
        if (a0 == 192 && a1 == 0 && (a2 == 0 || a2 == 2)) return false;              // 192.0.0/24 IETF, 192.0.2/24 docs
        if (a0 == 198 && (a1 == 18 || a1 == 19)) return false;                       // benchmarking
        if (a0 == 198 && a1 == 51 && a2 == 100) return false;                        // docs
        if (a0 == 203 && a1 == 0 && a2 == 113) return false;                         // docs
        return true;
    }

    /** The URL may not be fetched. The message is for logs; listeners only ever see "off the air". */
    public static final class Refused extends RuntimeException {
        public Refused(String why) { super(why); }
    }
}
