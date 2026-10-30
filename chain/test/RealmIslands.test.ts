// SPDX-License-Identifier: MIT
import { expect } from "chai";
import { ethers, network } from "hardhat";
import * as fs from "fs";
import * as path from "path";
import { time } from "@nomicfoundation/hardhat-network-helpers";

/**
 * RealmIslands (ADR-028): a deed mints only from a realm-signed voucher, only to the address in it,
 * only once per slot, only before its deadline; the seed is on chain; the owner can rotate the
 * signer and the metadata base; and a voucher signed by the Java server (fixture) is accepted.
 */
const DEED_TYPES = {
  Deed: [
    { name: "to", type: "address" },
    { name: "slot", type: "uint256" },
    { name: "seed", type: "uint64" },
    { name: "radius", type: "uint8" },
    { name: "deadline", type: "uint256" },
  ],
};
const BASE = "https://realm.example/api/v1/world/world-zero/tokens/";

async function deploy() {
  const [owner, player, realm, stranger] = await ethers.getSigners();
  const islands = await (await ethers.getContractFactory("RealmIslands")).deploy(owner.address, realm.address, BASE);
  const domain = {
    name: "RealmIslands",
    version: "1",
    chainId: (await ethers.provider.getNetwork()).chainId,
    verifyingContract: await islands.getAddress(),
  };
  const deadline = BigInt(await time.latest()) + 3600n;
  return { islands, owner, player, realm, stranger, domain, deadline };
}

describe("RealmIslands", () => {
  it("mints a deed from a realm voucher, with the seed on chain and metadata at baseURI + slot", async () => {
    const { islands, player, realm, stranger, domain, deadline } = await deploy();
    const deed = { to: player.address, slot: 3n, seed: 18446744073709551605n, radius: 18, deadline };
    const sig = await realm.signTypedData(domain, DEED_TYPES, deed);
    // Anyone may submit; the token still goes to deed.to.
    await expect(islands.connect(stranger).mint(deed, sig))
      .to.emit(islands, "DeedMinted").withArgs(3n, player.address, deed.seed, 18)
      .and.to.emit(islands, "Transfer").withArgs(ethers.ZeroAddress, player.address, 3n);
    expect(await islands.ownerOf(3n)).to.equal(player.address);
    expect(await islands.seedOf(3n)).to.equal(deed.seed);
    expect(await islands.radiusOf(3n)).to.equal(18);
    expect(await islands.tokenURI(3n)).to.equal(BASE + "3");
    expect(await islands.name()).to.equal("Realm Islands");
    expect(await islands.symbol()).to.equal("ISLE");
  });

  it("refuses a voucher not signed by the realm, or altered after signing", async () => {
    const { islands, player, realm, stranger, domain, deadline } = await deploy();
    const deed = { to: player.address, slot: 1n, seed: 42n, radius: 18, deadline };
    const forged = await stranger.signTypedData(domain, DEED_TYPES, deed);
    await expect(islands.mint(deed, forged)).to.be.revertedWithCustomError(islands, "NotRealmSigned");
    const sig = await realm.signTypedData(domain, DEED_TYPES, deed);
    await expect(islands.mint({ ...deed, to: stranger.address }, sig)).to.be.revertedWithCustomError(islands, "NotRealmSigned");
    await expect(islands.mint({ ...deed, seed: 43n }, sig)).to.be.revertedWithCustomError(islands, "NotRealmSigned");
    await expect(islands.mint({ ...deed, slot: 2n }, sig)).to.be.revertedWithCustomError(islands, "NotRealmSigned");
    // A voucher for another contract or chain does not work here either.
    const elsewhere = await realm.signTypedData({ ...domain, chainId: 11155111n }, DEED_TYPES, deed);
    await expect(islands.mint(deed, elsewhere)).to.be.revertedWithCustomError(islands, "NotRealmSigned");
  });

  it("mints a slot once and refuses an expired voucher", async () => {
    const { islands, player, realm, domain, deadline } = await deploy();
    const deed = { to: player.address, slot: 5n, seed: 7n, radius: 12, deadline };
    const sig = await realm.signTypedData(domain, DEED_TYPES, deed);
    await islands.mint(deed, sig);
    await expect(islands.mint(deed, sig)).to.be.revertedWithCustomError(islands, "ERC721InvalidSender");
    const late = { ...deed, slot: 6n };
    const lateSig = await realm.signTypedData(domain, DEED_TYPES, late);
    await time.increaseTo(deadline + 1n);
    await expect(islands.mint(late, lateSig)).to.be.revertedWithCustomError(islands, "VoucherExpired").withArgs(deadline);
  });

  it("lets only the owner rotate the signer and the metadata base; old vouchers die with the old key", async () => {
    const { islands, owner, player, realm, stranger, domain, deadline } = await deploy();
    const deed = { to: player.address, slot: 9n, seed: 1n, radius: 18, deadline };
    const old = await realm.signTypedData(domain, DEED_TYPES, deed);
    await expect(islands.connect(stranger).setSigner(stranger.address)).to.be.revertedWithCustomError(islands, "OwnableUnauthorizedAccount");
    await expect(islands.connect(owner).setSigner(ethers.ZeroAddress)).to.be.revertedWithCustomError(islands, "ZeroAddress");
    await expect(islands.connect(owner).setSigner(stranger.address)).to.emit(islands, "SignerChanged").withArgs(realm.address, stranger.address);
    await expect(islands.mint(deed, old)).to.be.revertedWithCustomError(islands, "NotRealmSigned");
    await islands.mint(deed, await stranger.signTypedData(domain, DEED_TYPES, deed));
    await expect(islands.connect(stranger).setBaseURI("x")).to.be.revertedWithCustomError(islands, "OwnableUnauthorizedAccount");
    await expect(islands.connect(owner).setBaseURI("ipfs://deeds/")).to.emit(islands, "BaseURIChanged").withArgs("ipfs://deeds/");
    expect(await islands.tokenURI(9n)).to.equal("ipfs://deeds/9");
    // Ownership moves in two steps: a mistyped address cannot take the contract.
    await islands.connect(owner).transferOwnership(stranger.address);
    expect(await islands.owner()).to.equal(owner.address);
    await islands.connect(stranger).acceptOwnership();
    expect(await islands.owner()).to.equal(stranger.address);
  });

  it("refuses a zero signer at deploy", async () => {
    const [owner] = await ethers.getSigners();
    const F = await ethers.getContractFactory("RealmIslands");
    await expect(F.deploy(owner.address, ethers.ZeroAddress, BASE)).to.be.revertedWithCustomError(F, "ZeroAddress");
  });

  it("accepts the voucher the Java realm signed (daedalus-wallet DeedVoucher)", async () => {
    const fx = JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "java-deed-voucher.json"), "utf8"));
    // Fresh chain: account 0's first deployment lands at the fixture's contract address.
    await network.provider.request({ method: "hardhat_reset", params: [] });
    const [owner, , realm] = await ethers.getSigners();
    expect(realm.address.toLowerCase()).to.equal(fx.signer);
    const islands = await (await ethers.getContractFactory("RealmIslands")).deploy(owner.address, realm.address, BASE);
    expect((await islands.getAddress()).toLowerCase()).to.equal(fx.contract);
    const deed = { to: fx.deed.to, slot: BigInt(fx.deed.slot), seed: BigInt(fx.deed.seed), radius: fx.deed.radius, deadline: BigInt(fx.deed.deadline) };
    expect(await islands.deedDigest(deed)).to.equal(fx.digest);
    await islands.mint(deed, fx.signature);
    expect((await islands.ownerOf(7n)).toLowerCase()).to.equal(fx.deed.to);
    expect(await islands.seedOf(7n)).to.equal(18446744073709551605n);
  });
});
