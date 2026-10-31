# `forge levels` and `forge loudness` refuse WAVs wider than 5.1

The analysis commands can't read a 7.1.4 or 9.1.6 WAV, which is the input `atmos-cbi` takes:

```text
$ forge levels check-714.wav
error: levels handles 1 to 6 channels (12 given)
$ forge loudness check-714.wav
error: 12 channels is not an AC-3 layout
```

So the loudness of an immersive source can't be checked before encoding, and an encode's
per-channel levels can't be compared with its input, without leaving iclforge. The height-level
issue was found with ffmpeg's `astats` for this reason.

## Suggested fix

- `levels`: report per-channel peak and RMS for any channel count, with labels from the WAV's
  channel mask or the CBI layout when there is one.
- `loudness`: measure BS.1770-4 integrated loudness with its per-channel weights, which cover any
  layout including heights. The same measurement can then serve `dialnorm=auto` for `atmos-cbi`
  (see the dialnorm issue).
