import logging

from Project2.registry import DEVICES, register

log = logging.getLogger(__name__)

# GPIO pins driven by PWM channel 1; everything else (18, 12, 10 SPI, 21 PCM) uses channel 0
_PWM1_PINS = {13, 19, 41, 45, 53}


@register(DEVICES, "ws281x")
class Ws281xDevice:
    """WS2811/WS2812(B)/SK6812 strip on a Raspberry Pi via rpi_ws281x.

    data_pin 18 (PWM) and 21 (PCM) need root; 10 (SPI) works without root
    if SPI is enabled. Don't use PWM pins together with onboard audio.

    brightness: 0..1 global dimming (done by the driver, keeps colors intact)
    gamma:      perceptual correction exponent (2.2 is typical, 1.0 = off)
    order:      byte order of the LEDs, "GRB" for WS2812B, "RGB", "GRBW" (SK6812)...
    reverse:    strip mounted the other way round (pixel 0 at the far end)
    """

    def __init__(self, count, data_pin=18, brightness=1.0, gamma=2.2, order="GRB",
                 reverse=False, freq_hz=800_000, dma=10, invert=False, channel=None):
        from rpi_ws281x import PixelStrip, ws  # Pi only; keeps the module importable on a dev machine

        strip_type = getattr(ws, f"WS2811_STRIP_{order.upper()}", None) \
            or getattr(ws, f"SK6812_STRIP_{order.upper()}", None)
        if strip_type is None:
            raise ValueError(f"ws281x: unknown LED order {order!r}")

        self.count, self.reverse = count, reverse
        self._strip = PixelStrip(
            count, data_pin, freq_hz=freq_hz, dma=dma, invert=invert,
            brightness=round(255 * min(1.0, max(0.0, brightness))),
            channel=channel if channel is not None else int(data_pin in _PWM1_PINS),
            strip_type=strip_type,
            gamma=[round(255 * (i / 255) ** gamma) for i in range(256)],
        )
        self._strip.begin()
        self._last = None
        log.info("ws281x: %d LEDs on GPIO%d (%s, brightness %.2f)", count, data_pin, order, brightness)

    def show(self, pixels):
        if pixels == self._last:
            return  # nothing changed, skip the DMA transfer
        self._last = list(pixels)
        ordered = reversed(pixels) if self.reverse else pixels
        # per index: rpi_ws281x's strip[:] = x fills every LED with the single value x
        for i, (r, g, b) in enumerate(ordered):
            self._strip[i] = (r << 16) | (g << 8) | b
        self._strip.show()

    def close(self):
        self._strip[:] = 0
        self._strip.show()  # leave the strip dark, not frozen on the last frame
