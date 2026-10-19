# Task 6 — PDDL Quality Assurance

## Overview

This task focuses on **quality assurance and validation of PDDL planning models** developed in Task 4 and Task 5.

The objective is to design test instances that demonstrate the correctness and reliability of single-agent and multi-agent path planning domains.

## Task Description

Design a set of PDDL problem instances to evaluate the behaviour of the planning models under different scenarios.

The test instances should demonstrate:

- **Single-Agent Path Planning:** Verify that a robot can reach its goal while avoiding stationary obstacles.
- **Multi-Agent Path Planning:** Verify that collision-aware planning can produce valid paths even when agents must take longer routes or wait to avoid conflicts.
- **Collision Avoidance:** Verify that vertex and edge (swapping) collisions are prevented.
- **Synchronized Movement:** Verify that more than two robots can coordinate their movements in lockstep.

## Implementation

The implementation focuses on designing PDDL problem instances compatible with the domain models developed in Tasks 4 and 5.

Each instance specifies:

- **Objects:** Robots, grid positions, and other relevant entities.
- **Initial State:** The starting positions and configurations of the robots.
- **Goal State:** The desired destination or final configuration for each robot.
- **Constraints:** Environmental conditions and movement restrictions defined by the domain model.

The instances are designed to test specific behaviours and potential limitations of the planning models.

## Testing

The test instances can be executed using [planning.domains](https://editor.planning.domains/).

Testing should verify that:

- The single-agent domain produces valid plans for solvable problems.
- The multi-agent domain generates collision-free plans when direct routes would cause conflicts.
- Vertex collisions are prevented.
- Edge (swapping) collisions are prevented.
- More than two robots can move in synchronized timesteps.
- Generated action sequences satisfy the goals and constraints of each test instance.

## Evaluation

Each test instance should be evaluated by examining:

- **Solvability:** Whether the planner successfully finds a solution.
- **Plan Validity:** Whether the generated plan satisfies the domain constraints.
- **Collision Avoidance:** Whether prohibited collisions are absent throughout execution.
- **Multi-Agent Coordination:** Whether robots execute coordinated movements correctly.
- **Goal Satisfaction:** Whether the final state satisfies the specified goals.

## Learning Outcomes

- Understanding quality assurance in automated planning.
- Designing test cases for PDDL domain models.
- Validating single-agent and multi-agent planning behaviour.
- Evaluating collision avoidance and synchronized movement.
- Identifying limitations and potential modelling errors through systematic testing.