Task 2 — Single-Agent Heuristic Design

Overview

This task focuses on designing and evaluating an improved heuristic function for A search* in a single-agent path planning environment.

The objective is to improve search performance on larger problems involving multiple single-errand tasks while maintaining a balance between heuristic informativeness and computational efficiency.

Task Description

Design a heuristic function that improves the performance of A* search.

The heuristic should consider two key aspects:

Informativeness: Reduce the number of nodes expanded during the search.

Efficiency: Minimise the computational time required to evaluate the heuristic at each node.

The goal is to achieve better overall search performance by balancing these two factors.

Implementation

The implementation builds upon the A* search algorithm developed in Task 1.

The main focus is designing a heuristic function that estimates the remaining cost to reach the goal while reducing unnecessary node expansions.

Evaluation

The heuristic is evaluated based on:

Node Expansions: The number of search nodes expanded.

Heuristic Computation Time: The time required to calculate heuristic values.

Overall Search Performance: The balance between search efficiency and heuristic informativeness.

Admissibility: Whether the heuristic avoids overestimating the true optimal cost to the goal.

The provided test cases assess heuristic informativeness. Additional performance measurements are needed to evaluate computational efficiency.

Learning Outcomes

Designing domain-specific heuristics for A* search.

Understanding the trade-off between heuristic informativeness and computational efficiency.

Evaluating heuristic admissibility and its relationship to optimality.

Comparing heuristic performance using node expansions and execution time.