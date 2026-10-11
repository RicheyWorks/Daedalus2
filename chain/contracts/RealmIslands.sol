// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

/**
 * @title Realm Islands
 * @notice The deeds of the Daedalus Realm (ADR-028). Token id = the island's lane slot; the island's
 * seed and radius are stored on chain, and the same seed always grows the same island, so the deed
 * carries the land itself, not a pointer to it.
 *
 * Minting is by voucher. The realm signs an EIP-712 `Deed` for the wallet that owns the island's
 * claim; anyone may submit it (and pay the gas), but the token goes only to `deed.to`. A slot can be
 * minted once (ERC-721 refuses a second mint). The realm's signing key holds no funds; rotating it is
 * `setSigner`. Metadata is `baseURI + slot`, served by the realm at /api/v1/world/{id}/tokens/{slot}.
 */
contract RealmIslands is ERC721, EIP712, Ownable2Step {
    /// @dev keccak256("Deed(address to,uint256 slot,uint64 seed,uint8 radius,uint256 deadline)")
    bytes32 public constant DEED_TYPEHASH =
        keccak256("Deed(address to,uint256 slot,uint64 seed,uint8 radius,uint256 deadline)");

    struct Deed {
        address to;
        uint256 slot;
        uint64 seed;
        uint8 radius;
        uint256 deadline;
    }

    /// @notice The realm key whose vouchers mint deeds.
    address public signer;
    /// @notice The island's seed and radius, as minted.
    mapping(uint256 slot => uint64) public seedOf;
    mapping(uint256 slot => uint8) public radiusOf;

    string private _base;

    event DeedMinted(uint256 indexed slot, address indexed to, uint64 seed, uint8 radius);
    event SignerChanged(address indexed previous, address indexed next);
    event BaseURIChanged(string uri);

    error ZeroAddress();
    error VoucherExpired(uint256 deadline);
    error NotRealmSigned(address recovered);

    constructor(address owner_, address signer_, string memory baseURI_)
        ERC721("Realm Islands", "ISLE")
        EIP712("RealmIslands", "1")
        Ownable(owner_)
    {
        if (signer_ == address(0)) revert ZeroAddress();
        signer = signer_;
        _base = baseURI_;
        emit SignerChanged(address(0), signer_);
        emit BaseURIChanged(baseURI_);
    }

    /// @notice The EIP-712 digest a voucher signs (the realm computes the same bytes in Java).
    function deedDigest(Deed calldata deed) public view returns (bytes32) {
        return _hashTypedDataV4(
            keccak256(abi.encode(DEED_TYPEHASH, deed.to, deed.slot, deed.seed, deed.radius, deed.deadline))
        );
    }

    /// @notice Redeem a realm voucher: mints token `deed.slot` to `deed.to`.
    function mint(Deed calldata deed, bytes calldata signature) external {
        if (block.timestamp > deed.deadline) revert VoucherExpired(deed.deadline);
        address recovered = ECDSA.recover(deedDigest(deed), signature);
        if (recovered != signer) revert NotRealmSigned(recovered);
        seedOf[deed.slot] = deed.seed;
        radiusOf[deed.slot] = deed.radius;
        emit DeedMinted(deed.slot, deed.to, deed.seed, deed.radius);
        _safeMint(deed.to, deed.slot);
    }

    function setSigner(address next) external onlyOwner {
        if (next == address(0)) revert ZeroAddress();
        emit SignerChanged(signer, next);
        signer = next;
    }

    function setBaseURI(string calldata uri) external onlyOwner {
        _base = uri;
        emit BaseURIChanged(uri);
    }

    function _baseURI() internal view override returns (string memory) {
        return _base;
    }
}
