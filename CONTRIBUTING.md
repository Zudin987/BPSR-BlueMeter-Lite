# Contributing

Bug reports and focused pull requests are welcome.

## Reporting bugs

Use the GitHub bug-report template and include:

- BlueMeter Lite version
- phone model
- Android version
- BPSR region/client
- clear reproduction steps
- a screenshot when relevant

Do not post raw packet captures or sensitive network information publicly.

## Pull requests

Keep changes focused on the lightweight Android meter.

Before submitting:

1. preserve the BPSR-only VPN allow-list
2. preserve upstream and AGPL attribution
3. run the patch against current BlueMeter Mobile
4. confirm the GitHub Actions APK build succeeds
5. update documentation for user-visible changes

Large features such as detailed encounter history, skill analysis, radar and cloud services are outside the current Lite scope unless discussed first.
