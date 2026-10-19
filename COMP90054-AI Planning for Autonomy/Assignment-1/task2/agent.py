import numpy as np
from queue import PriorityQueue
from typing import List, Tuple, Dict, Optional, Set, Any, Callable
from collections import deque
from environment import MultiAgentPathfindingEnv, Robot, Task, Errand, Action, Direction
import random
from dataclasses import dataclass, field
from hiddenagent import HiddenAgent

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

class SinglePathPlanningAgent(HiddenAgent):

    def choose_action(self, obs: np.ndarray) -> Any:
        """
        Choose an action based on the current observation.
        """
        # Check if agent has an assigned task
        robot = self.env.robots[0]  # Assuming single agent for this class
        current_errand = -1
        tasks = [(task.get_current_errand().target_x, task.get_current_errand().target_y) for task in self.env.tasks if task.id in self.env.get_unassigned_tasks()]
        if not hasattr(self, 'current_actions'):
            self.current_actions = self.a_star((robot.x, robot.y), tasks)
        
        for task_id, task_pos in zip(self.env.get_unassigned_tasks(),tasks):
            if (robot.x, robot.y) == task_pos:
                current_errand = task_id
                return ([Action.WAIT], [task_id])

        if self.current_actions:
            action = self.current_actions.pop(0)
            return ([action], [-1])

      
        # Default action if no task or path
        return ([Action.WAIT], [-1])  # Wait and no task assignment

    # ============================================================================
    # TASK 2: SINGLE AGENT HEURISTIC DESIGN
    # ============================================================================
    # Implement a heuristic for multiple tasks for a single agent

    def task_heuristic_single_agent(self, state: Dict[str, Any], available_tasks: List[Tuple[int,int]]) -> int:
        if not available_tasks:
            return 0
    
        robot_pos = (state['robots'][0][1], state['robots'][0][2])#start location
        tasks = list(dict.fromkeys(available_tasks))#duplicate reduction automatically
        grid = state.get('grid', self.env.grid)
        h, w = grid.shape
    
        # BFS cache to reduce time waste
        signature = grid.tobytes()
        if not hasattr(self, '_signature') or self._signature != signature:
            self._signature, self._cache = signature, {}
    
        def bfs(source):# bfs
            if source in self._cache:
                return self._cache[source]# avoid repeation
            dist = {source: 0}
            q = deque([source])#Initialize
            while q:
                x, y = q.popleft()
                for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] == 0 and (nx,ny) not in dist:
                        dist[(nx,ny)] = dist[(x,y)] + 1
                        q.append((nx,ny))
            self._cache[source] = dist
            return dist
    
        def d(a, b):
            return bfs(b).get(a, float('inf')) if a != b else 0
    
        nearest = min(d(robot_pos, t) for t in tasks)
        if nearest == float('inf') or len(tasks) == 1:
            return int(nearest) if nearest != float('inf') else 10**9
    
        # MST
        n = len(tasks)
        in_tree, min_edge = [False]*n, [float('inf')]*n
        min_edge[0] = 0
        mst = 0
        for _ in range(n):
            idx = min((i for i in range(n) if not in_tree[i]), key=lambda i: min_edge[i])
            in_tree[idx] = True
            mst += min_edge[idx]
            for j in range(n):
                if not in_tree[j]:
                    min_edge[j] = min(min_edge[j], d(tasks[idx], tasks[j]))
    
        return int(nearest + mst)   



if __name__ == "__main__":
    env = MultiAgentPathfindingEnv(num_robots=1,seed=3,max_errands_per_task=1,task_reveal_rate=0, tasks_per_robot=7, max_timesteps=40,show_all_tasks=True) 
    agent = SinglePathPlanningAgent(env)
    agent.run(iterations=1, display=True)
  
