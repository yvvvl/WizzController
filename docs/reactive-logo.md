# Reactive logo colour

The sidebar WizZ mark and the small title-bar icon share one tint. With
**exactly one configured, online, lit bulb**, they follow its displayed
colour. With several bulbs, or if the only bulb is off/unavailable, they use
the selected theme's accent. The **live brand accent** setting can disable
light-driven tinting and keep the theme accent.

Cycling through several bulb colours was removed because it did not identify
which bulb the mark represented. For one bulb, LAN-reported RGB changes and
virtual animated-scene frames update it with a short transition. The logo does
not send any extra light commands. Reduced-motion mode removes the transition.

An actual WiZ dynamic scene may report only a scene ID, not its instantaneous
LED colour. In that case WizZ shows a representative scene colour; it does not
claim exact physical synchronisation. If live RGB is reported, the logo uses
that value.

For a hardware-free check, run with `WIZZ_DEV_VIRTUAL_BULBS=1`, change colour
or start a dynamic scene, then repeat with `WIZZ_DEV_VIRTUAL_BULBS=3`. The
first should follow the virtual light; the second should use the theme accent.
