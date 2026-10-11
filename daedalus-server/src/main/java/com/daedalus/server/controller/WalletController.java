// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.DeedVoucherResponse;
import com.daedalus.api.dto.LoginResponse;
import com.daedalus.api.dto.WalletConfigResponse;
import com.daedalus.api.dto.WalletNonceResponse;
import com.daedalus.api.dto.WalletSignInRequest;
import com.daedalus.server.config.WalletProperties;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.security.JwtTokenService;
import com.daedalus.server.service.WorldHub;
import com.daedalus.server.service.WorldService;
import com.daedalus.server.web.ResourceNotFoundException;
import com.daedalus.wallet.DeedSigner;
import com.daedalus.wallet.DeedVoucher;
import com.daedalus.wallet.EthereumAddress;
import com.daedalus.wallet.SiweMessage;
import com.daedalus.wallet.SiweVerifier;
import com.daedalus.wallet.WalletNonces;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.security.Principal;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Optional;
import java.util.function.Supplier;

/**
 * Wallet sign-in and island deed vouchers (ADR-028). Mounted only with
 * {@code daedalus.wallet.enabled=true}.
 *
 * <p><b>Sign-in.</b> {@code GET /nonce?address=} returns the full Sign-In with Ethereum message; the
 * wallet signs it unchanged; {@code POST} with the signature returns the same JWT as the admin login,
 * whose subject is the lowercase address. From then on the address <em>is</em> the player: it claims
 * islands, builds, and names builders (ADR-026's "a signed-in caller is who they are").
 *
 * <p><b>Deeds.</b> The owner of a claimed island asks for a voucher and redeems it on the
 * RealmIslands contract. The realm signs only for the claim's owner and only when the owner is a
 * wallet address.
 */
@RestController
@RequestMapping("/api/v1")
@ConditionalOnProperty(name = "daedalus.wallet.enabled", havingValue = "true")
@Tag(name = "Wallet", description = "Sign in with Ethereum; island deed vouchers.")
public class WalletController {

    private static final Logger LOG = LoggerFactory.getLogger(WalletController.class);
    static final String STATEMENT = "Sign in to the Daedalus Realm.";
    static final Duration MESSAGE_TTL = Duration.ofMinutes(10);

    private final WalletProperties props;
    private final JwtTokenService tokens;
    private final WorldHub hub;
    private final WalletNonces nonces = new WalletNonces(MESSAGE_TTL, 10_000);
    private final SiweVerifier verifier;
    private final DeedSigner deedKey;
    private Supplier<Instant> clock = Clock.systemUTC()::instant;

    /** World Zero alone (tests). */
    public WalletController(WalletProperties props, JwtTokenService tokens, WorldService worlds) {
        this(props, tokens, WorldHub.of(worlds));
    }

    @org.springframework.beans.factory.annotation.Autowired
    public WalletController(WalletProperties props, JwtTokenService tokens, WorldHub hub) {
        this.props = props;
        this.tokens = tokens;
        this.hub = hub;
        this.verifier = new SiweVerifier(props.domain(), props.chainId(), Duration.ofMinutes(1));
        this.deedKey = props.deedSignerKey().isEmpty() ? null : DeedSigner.fromHex(props.deedSignerKey());
        if (deedKey != null) {
            // The deploy script needs this as REALM_SIGNER. An address is public; the key never leaves.
            LOG.info("Island deed vouchers are signed by {} (chain {}, contract {})", deedKey.address(),
                    props.chainId(), props.deedContract().isEmpty() ? "not yet deployed" : props.deedContract());
        }
    }

    /** Replace the clock (tests). */
    void useClock(Supplier<Instant> clock) {
        this.clock = clock;
    }

    @GetMapping("/auth/wallet/config")
    @Operation(summary = "The chain, the deed contract and the realm's voucher-signing address.")
    public WalletConfigResponse config() {
        boolean deeds = deedKey != null && EthereumAddress.normalize(props.deedContract()).isPresent();
        return new WalletConfigResponse(props.chainId(), props.deedContract(),
                deedKey == null ? "" : deedKey.address(), deeds);
    }

    @GetMapping("/auth/wallet/nonce")
    @Operation(summary = "The Sign-In with Ethereum message for this address to sign (single use, 10 minutes).")
    @PerKeyRateLimit("authLogin")
    public ResponseEntity<WalletNonceResponse> nonce(@RequestParam String address) {
        if (EthereumAddress.normalize(address).isEmpty()) {
            throw new IllegalArgumentException("address must be a 0x Ethereum address");
        }
        Instant now = clock.get().truncatedTo(java.time.temporal.ChronoUnit.SECONDS);
        String nonce = nonces.issue(now);
        SiweMessage m = new SiweMessage(props.domain(), EthereumAddress.checksummed(address), STATEMENT, props.uri(),
                props.chainId(), nonce, now, now.plus(MESSAGE_TTL));
        return ResponseEntity.ok(new WalletNonceResponse(m.toText(), nonce, m.expirationTime()));
    }

    @PostMapping("/auth/wallet")
    @Operation(summary = "Exchange a signed sign-in message for a JWT whose subject is the wallet address.",
            description = "401 with a reason (WRONG_DOMAIN, WRONG_CHAIN, EXPIRED, NOT_YET_VALID, BAD_SIGNATURE, "
                    + "STALE_NONCE, MALFORMED) on any failure. A nonce works once.")
    @PerKeyRateLimit("authLogin")
    public ResponseEntity<LoginResponse> signIn(@Valid @RequestBody WalletSignInRequest body) {
        SiweVerifier.Outcome out = verifier.verify(body.message(), body.signature(), nonces, clock.get());
        if (!out.ok()) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).header("X-Wallet-Refused", out.reason()).build();
        }
        JwtTokenService.IssuedToken issued = tokens.issue(out.address());
        return ResponseEntity.ok(new LoginResponse(issued.token(), issued.expiresAt()));
    }

    @PostMapping("/world/{id}/islands/{slot}/deed-voucher")
    @Operation(summary = "The island's owner gets a signed voucher to mint its deed on chain.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<DeedVoucherResponse> deedVoucher(@PathVariable String id, @PathVariable int slot,
            Principal principal, @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false) String bearer) {
        Optional<String> caller = caller(principal, bearer);
        if (caller.isEmpty()) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).header("X-Wallet-Refused", "SIGN_IN").build();
        }
        if (deedKey == null || EthereumAddress.normalize(props.deedContract()).isEmpty()) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).header("X-Wallet-Refused", "DEEDS_OFF").build();
        }
        WorldService worlds = hub.resolve(id);
        if (worlds.inspect(id) == null) {
            throw ResourceNotFoundException.world(id);
        }
        WorldService.IslandEntry isle = worlds.islands(id).stream().filter(e -> e.slot() == slot).findFirst()
                .orElseThrow(() -> ResourceNotFoundException.island(slot));
        WorldService.IslandClaim claim = worlds.claims(id).get(slot);
        if (claim == null || claim.owner().isEmpty() || !EthereumAddress.equalsNormalized(claim.owner(), caller.get())) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN).header("X-Wallet-Refused", "NOT_OWNER").build();
        }
        long deadline = clock.get().plus(Duration.ofMinutes(props.voucherMinutes())).getEpochSecond();
        DeedVoucher v = new DeedVoucher(caller.get(), slot, isle.seed(), isle.radius(), deadline, props.chainId(),
                props.deedContract());
        return ResponseEntity.ok(new DeedVoucherResponse(v.to(), slot, v.seedUint64(), isle.radius(), deadline,
                props.chainId(), v.contract(), deedKey.sign(v)));
    }

    /**
     * The signed-in wallet. In prod the security chain has already decoded the token into the
     * principal; on an open dev server nothing has, so the bearer token is checked here. Either way
     * it must be a wallet address, never a body field.
     */
    private Optional<String> caller(Principal principal, String bearer) {
        String who = principal == null ? null : principal.getName();
        if (who == null && bearer != null && bearer.startsWith("Bearer ")) {
            try {
                who = tokens.decoder().decode(bearer.substring(7).trim()).getSubject();
            } catch (RuntimeException e) {
                return Optional.empty();
            }
        }
        return EthereumAddress.normalize(who);
    }
}
