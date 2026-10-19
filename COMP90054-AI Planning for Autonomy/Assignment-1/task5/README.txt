Task 5 — Multi-Agent Path Planning in PDDL

Overview

This task focuses on modelling Multi-Agent Pathfinding (MAPF) using the Planning Domain Definition Language (PDDL).

The objective is to develop a collision-aware planning model that allows multiple robots to navigate a shared grid environment simultaneously while avoiding conflicts between their movements.

Task Description

Design a PDDL domain model that supports coordinated movement among multiple robots.

The model should address two types of collisions:

Vertex Collision: Two or more robots occupy the same position at the same timestep.

Edge (Swapping) Collision: Two robots exchange positions during the same timestep.

The model should prevent these collisions while allowing valid movement patterns, including:

Following Movements: A robot moves into a position vacated by another robot during the same timestep.

Cycle Movements: Multiple robots move simultaneously in a cycle without violating collision constraints.

Implementation

The implementation uses PDDL predicates and action schemas to represent robot positions, movement decisions, and collision constraints.

A synchronized movement approach is designed around the following process:

Action Selection: Each robot selects its intended movement or rotation.

Position Reservation: Robots reserve their intended destination positions to prevent conflicting movements.

Collision Checking: The model checks for vertex and swapping conflicts.

Synchronized State Update: Once all robots have selected their actions, a shared timestep advances and updates their positions.

This approach separates action selection from movement execution, allowing multiple robots to move in lockstep rather than updating their positions sequentially.

Testing

The domain and problem instances can be tested using planning.domains.

Testing should verify that:

Robots can navigate towards their respective goals.

Vertex collisions are prevented.

Edge (swapping) collisions are prevented.

Following and cycle movements remain possible.

Multiple robots can move in synchronized timesteps.

The generated plans satisfy the defined movement constraints.

Learning Outcomes

Understanding Multi-Agent Pathfinding (MAPF).

Modelling multi-agent planning problems using PDDL.

Identifying and preventing vertex and edge collisions.

Designing synchronized movement mechanisms.

Coordinating multiple autonomous agents in a shared environment.

Applying automated planning to collision-aware pathfinding problems.