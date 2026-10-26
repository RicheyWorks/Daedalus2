# Ocean passenger session integrity

A saved passenger belongs to the exact controller and vessel used at boarding.
Possessing a different vessel does not transfer that passenger session. An exit
request on that other vessel must leave possession and the hidden passenger
unchanged. Returning to the original vessel permits the normal dock exit.

Host dock configuration is immutable while a valid controller has a saved live
avatar. This keeps a reload from deleting, moving or changing the realm of its
return dock. ConfigureHost refuses before changing either registry or world
positions. Once that passenger exits, configuration can be replaced normally.
Multiple passengers must all exit before a reload is accepted.

This is not disconnect/death recovery, persistence or cross-server transfer.
Destroyed vessels and abandoned passengers still need a coordinated lifecycle
policy; invalid weak references do not establish a successful recovery. Do not
use a configuration reload as a substitute for evacuating active passengers.

Verification passed: fresh complete plugin build (128 files, 44 actions, 187.99 seconds), followed by a four-action test cleanup rebuild (7.30 seconds). All 128 final inputs match committed source 3d32f635. Both runtime tests passed with zero test errors/warnings, covering wrong
vessel rejection, saved avatar preservation, refusal to erase live dock data,
continued route resolution after refusal, and reconfiguration after exit.
