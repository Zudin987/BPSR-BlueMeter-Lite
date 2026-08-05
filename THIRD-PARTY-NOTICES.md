# Third-party notices

This file records third-party projects directly used by or incorporated into
BlueMeter Lite.

## BlueMeter Mobile

- Project: BlueMeter Mobile
- Repository: https://github.com/jbourny/bluemetermobile
- Author: jbourny and contributors
- Revision used by the current BlueMeter Lite build:
  `3c9d757cc0fd67971faf18447638c08044fb9b7c`
- License: GNU Affero General Public License version 3

BlueMeter Lite is built by checking out this exact upstream revision and
applying a patch set. The resulting Android application is a modified
derivative of BlueMeter Mobile.

The complete GNU AGPL v3 text is provided in the repository's `LICENSE` file.
Upstream copyright, license and acknowledgement notices remain applicable.

BlueMeter Mobile itself acknowledges the PC BlueMeter project and bptimer.com.
Those upstream acknowledgements are preserved in the corresponding upstream
source. BlueMeter Lite removes the BPTimer startup/reporting integration from
its Lite build.

## BPSR-ZDPS

- Project: BPSR-ZDPS
- Repository: https://github.com/Blue-Protocol-Source/BPSR-ZDPS
- Copyright: Copyright (c) 2025 Blue-Protocol-Source
- License: MIT License

BlueMeter Lite uses BPSR-ZDPS data and protocol references, including scene
ID/name data, profession or specialization mappings, and scene-entry packet
behaviour. BlueMeter Lite's Android/Dart implementation is maintained
separately, but the referenced ZDPS material remains subject to the MIT notice
below.

### MIT License

Copyright (c) 2025 Blue-Protocol-Source

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Scope of this notice

As of the reviewed v1.4.1 patch kit, no direct incorporation was identified
from these separately maintained projects:

- dmlgzs/StarResonanceDamageCounter
- winjwinj/bpsr-logs
- woheedev/bptimer

They do not need to be listed as BlueMeter Lite dependencies merely because
they solve the same problem or decode parts of the same game protocol. Add
their notices later if code, copyrightable tables, assets or documentation
from them are actually incorporated.
