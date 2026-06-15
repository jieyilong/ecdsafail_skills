Peak 2025->2006 via SHIFT22_FOLD_DIRTY: route the pair1-mul1 Solinas-fold shift22
spill/pos-32 adds through dirty venting (the from-zero product low-half `lo` is a
dead co-resident donor until the multiply uncompute), eliminating the ~257-wide
clean padded transient at the binder. Affine clamped to mfw=234; K0=21 reroll
restores a clean margin=0 island. Peak-for-Toffoli trade (+~15k T, -19 peak).
9024/9024 clean (0 classical/0 phase/0 ancilla). 2,575,683 T x 2006 = 5,166,820,098.

