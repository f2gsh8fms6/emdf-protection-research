# `atmos-cbi`: height and back bed channels reconstruct 3 dB low

In a channel-based immersive (CBI) encode, JOC reconstructs every bed channel outside the base
L/C/R/Ls/Rs ring 3 dB below its input level. That covers Lb/Rb, Tfl/Tfr, Tbl/Tbr and the 9.1.6
extras. L and R come back at their input level. tvOS shows the same shortfall, so the problem is in
the encoder.

## Evidence

The input was a 42 s 7.1.4 WAV with pink-noise bursts on L, R, Tfl, Tfr, Tbl and Tbr. It was
encoded at 768 kbit/s by DEE 5.2.1 and by `forge atmos-cbi in.wav out.ec3 768 7.1.4`. Each
stream's JOC objects were exported with `forge decode <in.ec3> <out.wav> <objects_dir>` and
measured as whole-file RMS in dBFS:

| Channel | Input | DEE encode | iclforge encode | iclforge minus input |
|---|---|---|---|---|
| L | -34.69 | -34.79 | -34.70 | 0.0 |
| R | -34.86 | -34.96 | -34.87 | 0.0 |
| Tfl | -34.21 | -34.37 | -37.22 | -3.0 |
| Tfr | -34.34 | -34.49 | -37.35 | -3.0 |
| Tbl | -33.96 | -34.10 | -36.99 | -3.0 |
| Tbr | -34.07 | -34.23 | -37.11 | -3.0 |

The same decoder recovers DEE's heights within 0.2 dB, so the decoder is not the cause. tvOS
27.0's in-process decode of the iclforge stream showed the same height shortfall. The input had no
Lb/Rb content, so those channels are untested, but they take the same code path.

## Cause

The bed constructor of `AtmosEncoder::Impl` (`libs/ac3/src/oba/atmos.cpp`) gives each channel
outside the base ring `bed_scale_ = kExtensionDownmixScale` (0.7071, -3 dB). That is the headroom
the channel is folded into the 5.1 bed with. `AtmosEncoder::encode_bed_frame` then calls:

```cpp
impl_->render_and_reconstruct(audio, impl_->bed_pan_, target, impl_->bed_scale_, target_lfe);
```

`render_and_reconstruct` folds `scale` into each essence's power (`power = signal * scale^2`) and
solves `M = P D^T (D P D^T + eps I)^-1` with D taken from the unscaled `bed_pan_`. That estimator
returns `scale * signal`. This is correct for a dynamic object, where `scale` is the object's own
gain. For a bed channel, `scale` is only downmix headroom, so the channel comes back at 0.7071
(-3.01 dB). That matches the measurement.

The comment above `kExtensionDownmixScale` says JOC "recovers each channel at its OWN original
level regardless of what this constant is". The measurement contradicts that comment.

## Suggested fix

Give the solve the scaled gains and unit power for bed channels, so M reconstructs the channel at
unity:

```cpp
const std::vector<double> unity(target.size(), 1.0);
impl_->render_and_reconstruct(audio, target, target, unity, target_lfe);
```

Update the comment as well, and add a test that a CBI encode reconstructs a lone height channel at
its input level within 0.5 dB.
