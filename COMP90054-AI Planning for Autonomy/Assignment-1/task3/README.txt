# Task 3 — Single-Agent Task Scheduling

## Overview

This task focuses on designing a **single-agent task scheduling algorithm** to maximise the number of tasks completed within a limited time period.

Building upon the A* path planning algorithm developed in Task 1, the objective is to determine an efficient order for completing multiple tasks while considering travel costs and time constraints.

## Task Description

Implement the `assign_tasks_single_agent` method to select the next task for a robot.

The method takes two inputs:

- **`position`:** The robot's current position.
- **`available_tasks`:** A list of tasks available for completion.

The method returns the index of the task that the robot should attempt first.

The scheduling strategy should:

- Prioritise tasks based on their estimated completion costs.
- Consider the travel distance between the robot and task locations.
- Account for the limited time available.
- Aim to maximise the total number of completed tasks.

## Implementation

The implementation focuses on developing a task selection strategy that integrates scheduling decisions with path planning.

The existing `self.a_star()` method from Task 1 can be used to calculate paths and estimate travel costs.

Unlike the previous tasks, no specific scheduling algorithm is prescribed. The approach requires designing a suitable strategy for selecting tasks under time constraints.

## Evaluation

The scheduling strategy can be evaluated based on:

- **Task Completion Rate:** The number of tasks completed within the available time.
- **Travel Cost:** The total movement cost required to complete selected tasks.
- **Scheduling Efficiency:** The computational cost of selecting the next task.
- **Task Prioritisation:** How effectively the scheduling strategy chooses tasks to maximise overall task completion.

The provided test cases offer a way to assess the scheduling approach, but they do not guarantee that the strategy is optimal.

## Learning Outcomes

- Designing scheduling strategies for autonomous agents.
- Integrating A* path planning with task scheduling.
- Optimising task completion under time constraints.
- Applying heuristic decision-making to task prioritisation.
- Evaluating scheduling strategies using performance metrics.