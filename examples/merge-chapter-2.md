# Lecture 2. Genetics and Heredity

## 1. Mendel's laws

Gregor Mendel formulated the fundamental laws of heredity.

### First law (uniformity)

All hybrids of the first generation F~1~ are uniform.

### Second law (segregation)

In F~2~ a segregation of **3:1** is observed.

## 2. Molecular genetics

DNA carries the genetic information.

```python
# Complementary base pairs
pairs = {"A": "T", "T": "A", "G": "C", "C": "G"}

def complement(strand):
    return "".join(pairs[base] for base in strand)
```

### DNA structure

A double helix with a sugar–phosphate backbone and nitrogenous bases.

## 3. Mutations

Types of mutations:

1. Gene (point) mutations
2. Chromosomal
3. Genomic

```chart
type: pie
title: Mutation Type Frequency
Gene: 60
Chromosomal: 25
Genomic: 15
```

## 4. Practical applications

Genetic engineering allows modification of an organism's DNA.

- [x] Sequencing of the human genome
- [x] CRISPR-Cas9 technology
- [ ] Gene therapy for every disease

[^ref1]: Watson J.D., Crick F.H. *Molecular Structure of Nucleic Acids*, Nature, 1953.
