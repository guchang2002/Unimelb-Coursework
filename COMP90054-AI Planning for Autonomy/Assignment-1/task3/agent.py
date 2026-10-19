import numpy as np
from queue import PriorityQueue
from typing import List, Tuple, Dict, Optional, Set, Any, Callable
from collections import deque
from environment import MultiAgentPathfindingEnv, Robot, Task, Errand, Action, Direction
import random
from dataclasses import dataclass, field
from hiddenagent import SinglePathPlanningAgent

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

class SingleTaskSchedulingAgent(SinglePathPlanningAgent):

    def choose_action(self, obs: np.ndarray) -> Any:
        """
        Choose an action based on the current observation.
        """
        if not hasattr(self, 'current_actions'):
            self.current_actions = []

        # Check if agent has an assigned task
        robot = self.env.robots[0]  # Assuming single agent for this class
        current_errand = None
        if robot.task_id is None or robot.task_id < 0:
            unassigned_tasks = [self.env.tasks[i] for i in self.env.get_unassigned_tasks()]
            task_id = self.assign_tasks_single_agent((robot.x, robot.y), unassigned_tasks)
            if task_id != -1:
                current_errand = self.env.tasks[task_id].get_current_errand()
        else:
            task_id = -1
            current_task = self.env.tasks[robot.task_id]
            current_errand = current_task.get_current_errand()

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
    # TASK 3: SINGLE AGENT TASK ASSIGNMENT
    # ============================================================================
    # Implement task assignment for a single agent

    def assign_tasks_single_agent(self, position: Tuple[int, int], available_tasks: List[Task]) -> int:
        if not available_tasks:
            return -1
        
        if len(available_tasks) == 1:
            return available_tasks[0].id
        
        # Time remaining_time
        remaining_time = self.env.max_timesteps - self.env.timestep
        
        # BFS
        grid = self.env.grid
        h, w = self.env.grid_height, self.env.grid_width
        
        if not hasattr(self, '_task3_signature') or self._task3_signature != grid.tobytes():
            self._task3_signature = grid.tobytes()
            self._task3_bfs_cache = {}
        
        def bfs(source):
            if source in self._task3_bfs_cache:
                return self._task3_bfs_cache[source]
            dist = {source: 0}
            q = deque([source])
            while q:
                x, y = q.popleft()
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and grid[ny, nx] == 0 and (nx, ny) not in dist:
                        dist[(nx, ny)] = dist[(x, y)] + 1
                        q.append((nx, ny))
            self._task3_bfs_cache[source] = dist
            return dist
        
        def get_distance(a, b):
            if a == b:
                return 0
            return bfs(b).get(a, float('inf'))
        
        #Collect information
        task_info = []
        for task in available_tasks:
            errand = task.get_current_errand()
            if errand is not None:
                # calculate cost
                total_cost = 0
                current = position
                feasible = True
                for e in task.errands[task.current_errand_idx:]:
                    d = get_distance(current, (e.target_x, e.target_y))
                    if d == float('inf'):
                        feasible = False
                        break
                    total_cost += d
                    current = (e.target_x, e.target_y)
                if feasible:
                    task_info.append((task.id, (errand.target_x, errand.target_y), total_cost, task))
        
        if not task_info:
            return -1
        
        n = len(task_info)
        

        # Brutal algorithm if task <=5
        if n <= 5:
            import itertools
            best_first = None
            best_count = -1
            best_time = float('inf')
            
            for perm in itertools.permutations(range(n)):
                total = 0
                current = position
                completed = 0
                
                for idx in perm:
                    task = task_info[idx][3]
                    task_cost = 0
                    pos = current
                    for e in task.errands[task.current_errand_idx:]:
                        d = get_distance(pos, (e.target_x, e.target_y))
                        if d == float('inf'):
                            task_cost = float('inf')
                            break
                        task_cost += d
                        pos = (e.target_x, e.target_y)
                    
                    if task_cost == float('inf'):
                        break
                    
                    if total + task_cost > remaining_time:
                        break
                    
                    total += task_cost
                    completed += 1
                    current = pos
                
                # If number of task is same, then choose the one with less time
                if completed > best_count:
                    best_count = completed
                    best_time = total
                    best_first = task_info[perm[0]][0] if completed > 0 else None
                elif completed == best_count and total < best_time:
                    best_time = total
                    best_first = task_info[perm[0]][0] if completed > 0 else None
            
            if best_first is not None:
                return best_first
        
        # Two step greedy
        dist_matrix = {}
        for i, (id1, pos1, _, _) in enumerate(task_info):
            for j, (id2, pos2, _, _) in enumerate(task_info):
                if i != j:
                    dist_matrix[(id1, id2)] = get_distance(pos1, pos2)
        
        best_task = None
        best_score = float('inf')
        # throughout all tasks
        for task_id, task_pos, task_cost, task in task_info:
            # get distance
            first_dist = get_distance(position, task_pos)
            
            if first_dist == float('inf'):
                continue
            
            # what if no task can be done
            if first_dist > remaining_time:
                continue
            
            # the "second" nearest distance
            end_pos = task_pos
            for e in task.errands[task.current_errand_idx:]:
                end_pos = (e.target_x, e.target_y)
            
            second_dist = min(
                (get_distance(end_pos, other_pos)
                for other_id, other_pos, _, _ in task_info if other_id != task_id),
                default=0
            )
            
            # first_dist + second_dist is the total two-step distance
            
            score = first_dist + second_dist
            if score < best_score:
                best_score = score
                best_task = task_id#choose the least score
        
        return best_task if best_task is not None else -1

if __name__ == "__main__":
    env = MultiAgentPathfindingEnv(num_robots=1,seed=2) 
    agent = SingleTaskSchedulingAgent(env)
    agent.run(iterations=1, display=True)
  
