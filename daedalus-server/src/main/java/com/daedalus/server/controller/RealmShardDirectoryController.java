// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.world.RealmLandGrid;
import java.net.URI;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/** Opt-in configured directory; does not migrate state, grant access or promise worker health. */
@RestController
@RequestMapping("/api/v1/realms")
@ConditionalOnProperty(name = "daedalus.shards.enabled", havingValue = "true")
public class RealmShardDirectoryController {
    private static final Pattern REALM = Pattern.compile("[a-z0-9][a-z0-9-]{0,63}");
    private final Map<String,String> routes;
    private final long revision;
    public record Route(String realm, int district, String serverUrl, long directoryRevision) {}

    public RealmShardDirectoryController(@Value("${daedalus.shards.routes:}") String config,
                                         @Value("${daedalus.shards.revision:1}") long revision) {
        if (revision < 1 || config.length() > 262144) throw new IllegalArgumentException("invalid directory revision/size");
        var parsed = new HashMap<String,String>();
        // realm,firstDistrict,lastDistrict,httpsOrigin ; repeated entries
        if (config.isBlank()) throw new IllegalArgumentException("enabled shard directory needs routes");
        for (String entry : config.split(";", -1)) {
            String[] p=entry.trim().split(",", -1);
            if (p.length!=4 || !REALM.matcher(p[0]).matches()) throw new IllegalArgumentException("invalid shard route");
            int first=Integer.parseInt(p[1]), last=Integer.parseInt(p[2]);
            if(first<0 || last>99 || first>last) throw new IllegalArgumentException("invalid district interval");
            URI uri=URI.create(p[3]);
            if(!"https".equals(uri.getScheme()) || uri.getHost()==null || uri.getUserInfo()!=null
                    || uri.getQuery()!=null || uri.getFragment()!=null || !(uri.getPath().isEmpty() || "/".equals(uri.getPath()))
                    || uri.getPort()>65535 || uri.getPort()==0)
                throw new IllegalArgumentException("shard URL must be a public HTTPS origin without credentials");
            String origin=p[3].endsWith("/")?p[3].substring(0,p[3].length()-1):p[3];
            for(int district=first;district<=last;district++) {
                if(parsed.putIfAbsent(p[0]+":"+district,origin)!=null)
                    throw new IllegalArgumentException("overlapping realm district assignments");
            }
        }
        routes=Map.copyOf(parsed);this.revision=revision;
    }

    @GetMapping("/{realm}/districts/{district}/route")
    public Route route(@PathVariable String realm, @PathVariable int district) {
        if(!REALM.matcher(realm).matches() || district<0 || district>=RealmLandGrid.SIDE)
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"invalid realm or district");
        String origin=routes.get(realm+":"+district);
        if(origin==null) throw new ResponseStatusException(HttpStatus.NOT_FOUND,"district is not assigned");
        return new Route(realm,district,origin,revision);
    }
}
