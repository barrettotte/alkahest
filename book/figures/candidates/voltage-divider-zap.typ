// Evaluation-only Zap source; the portable SVG is the publication input.
#import "@preview/zap:0.6.0"

#zap.circuit({
  import zap: *

  node("return", (0, 0))
  vsource("source", "return", (rel: (0, 4)), label: $V_s = 9 upright(V)$)
  node("top", (4, 4), fill: false)
  wire("source.out", "top")
  resistor("r1", "top", (rel: (0, -2)), label: $R_1 = 1 upright(k Omega)$)
  node("out", "r1.out", label: $V_"out" = 6 upright(V)$)
  resistor("r2", "out", (rel: (0, -2)), label: $R_2 = 2 upright(k Omega)$)
  wire("r2.out", "return")
  ground("ground", "return")
})
