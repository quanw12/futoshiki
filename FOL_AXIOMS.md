# Futoshiki FOL Axioms

Let the index domain be `D = {1, 2, ..., N}`.

Predicates:
- `Val(i,j,v)`: cell `(i,j)` has value `v`.
- `Given(i,j,v)`: cell `(i,j)` is pre-filled with `v`.
- `LessH(i,j)`, `GreaterH(i,j)`: horizontal inequality between `(i,j)` and `(i,j+1)`.
- `LessV(i,j)`, `GreaterV(i,j)`: vertical inequality between `(i,j)` and `(i+1,j)`.
- `Less(v1,v2)`: arithmetic background relation `v1 < v2`.
- `InRange(v)`: shorthand for `1 <= v <= N`.

## A1 - Existence (at least one value per cell)

\[
\forall i \forall j \; \exists v \; Val(i,j,v)
\]

Meaning: every grid position is assigned at least one candidate value.

## A2 - Functionality (at most one value per cell)

\[
\forall i \forall j \forall v_1 \forall v_2 \;
\big(Val(i,j,v_1) \land Val(i,j,v_2)\big) \Rightarrow v_1 = v_2
\]

Meaning: `Val` is single-valued on each cell (functional assignment).

## A3 - Row Uniqueness (all-different by row)

\[
\forall i \forall j_1 \forall j_2 \forall v \;
\big(Val(i,j_1,v) \land Val(i,j_2,v) \land j_1 \neq j_2\big) \Rightarrow \bot
\]

Equivalent form:
\[
\forall i \forall j_1 \forall j_2 \forall v \;
\big(j_1 \neq j_2 \Rightarrow \neg(Val(i,j_1,v) \land Val(i,j_2,v))\big)
\]

Meaning: a value cannot appear twice in the same row.

## A4 - Horizontal Inequality

\[
\forall i \forall j \forall v_1 \forall v_2 \;
\big(LessH(i,j) \land Val(i,j,v_1) \land Val(i,j+1,v_2)\big) \Rightarrow Less(v_1,v_2)
\]

\[
\forall i \forall j \forall v_1 \forall v_2 \;
\big(GreaterH(i,j) \land Val(i,j,v_1) \land Val(i,j+1,v_2)\big) \Rightarrow Less(v_2,v_1)
\]

Meaning: horizontal signs enforce strict ordering between adjacent cells.

## A5 - Given Clues Preservation

\[
\forall i \forall j \forall v \; Given(i,j,v) \Rightarrow Val(i,j,v)
\]

Meaning: each clue is a hard fact in the model.

## Missing Axiom 1 - Column Uniqueness

\[
\forall j \forall i_1 \forall i_2 \forall v \;
\big(Val(i_1,j,v) \land Val(i_2,j,v) \land i_1 \neq i_2\big) \Rightarrow \bot
\]

Equivalent form:
\[
\forall j \forall i_1 \forall i_2 \forall v \;
\big(i_1 \neq i_2 \Rightarrow \neg(Val(i_1,j,v) \land Val(i_2,j,v))\big)
\]

Meaning: each column also satisfies an all-different constraint.

## Missing Axiom 2 - Vertical Inequality Constraints

\[
\forall i \forall j \forall v_1 \forall v_2 \;
\big(LessV(i,j) \land Val(i,j,v_1) \land Val(i+1,j,v_2)\big) \Rightarrow Less(v_1,v_2)
\]

\[
\forall i \forall j \forall v_1 \forall v_2 \;
\big(GreaterV(i,j) \land Val(i,j,v_1) \land Val(i+1,j,v_2)\big) \Rightarrow Less(v_2,v_1)
\]

Meaning: vertical edges propagate strict partial order from top to bottom.

## Missing Axiom 3 - Completeness / Domain Restriction

Range soundness:
\[
\forall i \forall j \forall v \; Val(i,j,v) \Rightarrow InRange(v)
\]

where
\[
InRange(v) \equiv (1 \le v \le N)
\]

Equivalent finite-domain expansion:
\[
\forall i \forall j \forall v \;
Val(i,j,v) \Rightarrow (v=1 \lor v=2 \lor \cdots \lor v=N)
\]

Meaning: all assigned values remain inside the legal symbol domain.

## Optional Exactness Axiom (often used in grounded KB)

\[
\forall i \forall j \forall v \;
\Big(InRange(v) \land \neg\exists v' (v' \neq v \land Val(i,j,v'))\Big) \Rightarrow Val(i,j,v)
\]

Practical note: in finite model generation, exactness is usually enforced by combining A1 + A2 + range constraints after grounding.
