
import numpy as np
from queue import PriorityQueue
from typing import List, Tuple, Dict, Optional, Set, Any, Callable
from collections import deque
from environment import MultiAgentPathfindingEnv, Robot, Task, Errand, Action, Direction
import random
from dataclasses import dataclass, field

def manhattan_heuristic(state: Dict[str, Any], goal: Tuple[int, int]) -> float:
    """
    Heuristic function for A* algorithm using Manhattan distance.
    
    Args:
        state: Current state of the environment
        goal: Goal position (x, y)
    
    Returns:
        Estimated cost from current state to goal
    """
    robot_position = state['robots'][0][1:3]  # Assuming single agent for this class
    return abs(robot_position[0] - goal[0]) + abs(robot_position[1] - goal[1])

class BaseAgent:    
    """
    Base class for multi-agent pathfinding agents.
    
    This class provides basic functionality and should not be instantiated directly.
    Instead, use the PathfindingAgent subclass for actual implementations.
    """
    def __init__(self, env: MultiAgentPathfindingEnv):
        """
        Initialize the base agent with the environment.
        
        Args:
            env: The multi-agent pathfinding environment
        """
        self.env = env
        self.grid_width = env.grid_width
        self.grid_height = env.grid_height
        self.current_actions = []

    def run(self, iterations: int = 10, display: bool = False):
        """
        Run the agent's main loop.
        """
        for i in range(iterations):
            if i>0:
                obs,info = self.env.reset()
            else:
                obs = self.env._get_observation()
           
            terminated = False
            truncated = False
            while not terminated and not truncated:
                if display:
                    self.env.render()
                # Choose an action
                action = self.choose_action(obs)

                # Take a step in the environment
                obs, reward, terminated, truncated, info = self.env.step(action)
        
        return self.env.completed_tasks

    def choose_action(self, obs: np.ndarray) -> Any:
        """
        Choose an action based on the current observation.
        """
        # Not implemented in the base class
        raise NotImplementedError("This method should be overridden by subclasses.")

class SinglePathPlanningAgent(BaseAgent):
    """
    Agent for solving multi-agent pathfinding problems.
    
    This class provides a scaffold for implementing algorithms of increasing complexity.
    Students should implement methods in the order they appear.
    """
 
class SinglePathPlanningAgent(BaseAgent):
    """
    Agent for solving single-agent pathfinding problems.
    
    """
    def choose_action(self, obs: np.ndarray) -> Any:
        """
        Choose an action based on the current observation.
        """
        # Check if agent has an assigned task
        robot = self.env.robots[0]  # Assuming single agent for this class
        
        if robot.task_id is None or robot.task_id < 0:
            # No current task, assign the first pending task
            available_tasks = self.env.get_unassigned_tasks()
            if available_tasks:
                task_id = available_tasks[0]
                task = self.env.tasks[task_id]
                current_errand = task.get_current_errand()
        else:
            task_id = -1
            current_errand = self.env.tasks[robot.task_id].get_current_errand()
        

        if current_errand and not self.current_actions:
            goal = (current_errand.target_x, current_errand.target_y)
            start = (robot.x, robot.y)
            
            # Get path using A* (should return list of actions)
            actions = self.a_star(start, goal, manhattan_heuristic)
            if actions:
                self.current_actions = actions
                action = self.current_actions.pop(0)
                return ([action], [task_id])  # Return first action in path
        elif self.current_actions:
            action = self.current_actions.pop(0)
            return ([action], [task_id])  # Return next action in path

        # Default action if no task or path
        return ([Action.WAIT], [task_id])  # Wait and no task assignment    
    
    # ============================================================================
    # TASK 1: SINGLE AGENT PATH PLANNING
    # ============================================================================
    # Implement path planning for a single agent

    def a_star(self, start: Tuple[int, int], goal: Tuple[int, int], heuristic: Callable[[Dict[str, Any], Tuple[int, int]], float]) -> List[Action]:
        # STUDENT CODE HERE
        initial_state = self.env.get_state()
        robot = initial_state['robots'][0]
        direction0 = Direction(robot[3])
        start_node = (start[0], start[1], direction0)#get star-node location and direction

        counter = 0#use counter to avoid uncomparable

        start_h = heuristic(initial_state, goal)#h
        start_f = 0 + start_h#f=g+h，g_cost=0

        frontier = PriorityQueue()
        frontier.put((start_f, counter, start_node, []))#f,counter to avoid uncomparable,start_node,action
        
        g_cost: Dict[Tuple[int, int, Direction], int] = {start_node: 0}

        while not frontier.empty():
                
            _, _, current_node, current_actions = frontier.get()#no need counter and fscore
            x, y, direction = current_node
        

            if (x, y) == goal:
                return current_actions# if start is goal
        
            # get g_cost
            current_g = g_cost[current_node]
        
            current_state = self.env.get_state()
            current_state['robots'][0] = (0, x, y, direction, None)# curren node situation
        
            valid_moves, _ = self.env.get_valid_actions(current_state, robot_id=0)
        
            for action in valid_moves[0]:
                successor_state = self.env.get_successor(current_state, ([action], [-1]))
                _, nx, ny, nd, _ = successor_state['robots'][0]
                next_node = (nx, ny, Direction(nd))# throught out all possible moves and see its successor
            
                # new g_cost
                new_g = current_g + 1
            
                # if there's better g_cost
                if new_g < g_cost.get(next_node, float('inf')):
                    # renew
                    g_cost[next_node] = new_g
                
                    # h and f
                    h = heuristic(successor_state, goal)
                    new_f = new_g + h
                
                    # renew counter
                    counter += 1
                    new_actions = current_actions + [action]
                    frontier.put((new_f, counter, next_node, new_actions))
        return []

        # Hint: You can use self.env.get_state(), self.env.get_valid_actions(), and self.env.get_successor()
        # Hint: You may want to consider using your own definition of a state. The environment's state may have extra information that is not needed for pathfinding.
        # Hint: Consider using a priority queue for the frontier and a set for explored states



if __name__ == "__main__":
    env = MultiAgentPathfindingEnv(num_robots=1,seed=1, max_timesteps=100)
    agent = SinglePathPlanningAgent(env)
    agent.run(iterations=1, display=True)  

