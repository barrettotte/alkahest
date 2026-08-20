// Evaluate a Typst-native reaction scheme against the portable SVG workflow.
#import "@preview/typed-smiles:0.10.0": ce, mol, reaction, rxn-arrow, smiles

#set page(margin: 24pt)

#align(center, reaction(
  mol(smiles("CC(=O)O")),
  [+],
  mol(smiles("CCO")),
  rxn-arrow(),
  mol(smiles("CCOC(=O)C")),
  [+],
  ce("H2O"),
))
