Task 4 — Single-Agent Path Planning in PDDL

Overview

This task focuses on modelling single-agent path planning using the Planning Domain Definition Language (PDDL).

Instead of implementing search algorithms directly, the objective is to develop a planning domain that allows an automated planner to generate valid paths for a robot navigating a grid-based environment.

Task Description

Design a PDDL domain model for a single robot navigating an environment containing other stationary robots.

The domain should represent:

Robot Locations: The positions of robots within the environment.

Agent Position: The current location of the robot being controlled.

Robot Orientation: The direction each robot is facing.

Available Actions: The movement and rotation actions that the robot can perform.

Movement Constraints: Restrictions that prevent the controlled robot from moving into occupied or invalid locations.

The goal is to enable an automated planner to generate a valid sequence of actions that moves the controlled robot from its initial position to a specified destination.

Implementation

The implementation uses PDDL to describe the planning problem through two main components:

Domain File: Defines predicates, action schemas, preconditions, and effects governing robot behaviour.

Problem File: Specifies objects, the initial state, and the desired goal state.

Other robots are treated as stationary obstacles during the planning process.

The resulting model can be used with a compatible automated planner to generate action sequences.

Testing

The PDDL domain and problem instances can be developed and tested using planning.domains.

Testing should verify that:

The planner generates valid paths between start and goal positions.

Robot movements satisfy the defined action preconditions.

The controlled robot avoids stationary obstacles.

Robot orientation and movement constraints are correctly represented.

The generated action sequence reaches the intended goal state.

Learning Outcomes

Understanding automated planning and PDDL.

Representing planning problems using predicates and action schemas.

Defining action preconditions and effects.

Modelling robot movement and orientation in a grid environment.

Applying automated planners to single-agent pathfinding problems.