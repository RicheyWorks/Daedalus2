// SPDX-License-Identifier: MIT
package com.daedalus.server.service;

import com.daedalus.world.persistence.RealmRecordStore;
import java.io.IOException;
import java.nio.file.Path;
import java.util.Optional;
import org.springframework.beans.factory.DisposableBean;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

/** Explicitly enabled local host adapter; snapshot validation belongs to the authoritative rules owner. */
@Service
@ConditionalOnProperty(name = "daedalus.realm-record.enabled", havingValue = "true")
public class RealmRecordService implements DisposableBean {
    private final RealmRecordStore store;
    public RealmRecordService(@Value("${daedalus.realm-record.directory:}") String directory) throws IOException {
        if (directory.isBlank()) throw new IOException("Realm record directory must be explicitly configured");
        store = new RealmRecordStore(Path.of(directory));
    }
    public Optional<RealmRecordStore.Stored> read(String realm, String key) throws IOException { return store.read(realm, key); }
    public RealmRecordStore.Write compareAndSet(String realm, String key, long revision, byte[] payload) throws IOException {
        return store.compareAndSet(realm, key, revision, payload);
    }
    @Override public void destroy() throws IOException { store.close(); }
}
