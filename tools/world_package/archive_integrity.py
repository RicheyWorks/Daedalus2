# SPDX-License-Identifier: MIT
"""Bounded streaming integrity of every captured ZIP member, without extraction."""

CHUNK_BYTES = 64 * 1024


class ArchiveIntegrityError(ValueError):
    """A named member cannot pass the archive's integrity/expansion boundary."""


def validate_archive_integrity(archive, *, max_expanded_bytes, max_member_bytes=None):
    """Read all members to EOF, discard chunks and return unique expanded bytes.

    The caller checks names/types/member counts and declared expansion first.
    This pass independently enforces cumulative and per-member ACTUAL bytes;
    later parsing rereads are not charged to this unique expansion budget.
    """
    if max_member_bytes is None:
        max_member_bytes = max_expanded_bytes
    if any(type(limit) is not int or limit < 0 for limit in (max_expanded_bytes, max_member_bytes)):
        raise ArchiveIntegrityError("expanded-byte limits must be nonnegative integers")
    total = 0
    for entry in archive.infolist():
        member_total = 0
        try:
            with archive.open(entry, "r") as stream:
                while True:
                    # One extra byte distinguishes exact-budget EOF from
                    # overflow, without consuming another full 64 KiB chunk.
                    size = min(CHUNK_BYTES, max_expanded_bytes - total + 1,
                               max_member_bytes - member_total + 1)
                    chunk = stream.read(size)
                    if not chunk:
                        break
                    member_total += len(chunk)
                    total += len(chunk)
                    if member_total > max_member_bytes:
                        raise ArchiveIntegrityError(entry.filename + ": per-member expanded-byte budget exceeded")
                    if total > max_expanded_bytes:
                        raise ArchiveIntegrityError(entry.filename + ": cumulative expanded-byte budget exceeded")
            if member_total != entry.file_size:
                raise ArchiveIntegrityError(entry.filename + ": streamed size differs from declared size")
        except ArchiveIntegrityError:
            raise
        except Exception as error:
            # Covers CRC/decompressor/open/read/close failures at the member
            # boundary; never turns a partial integrity read into admission.
            raise ArchiveIntegrityError(entry.filename + ": cannot verify ZIP member: " + str(error)) from error
    return total
