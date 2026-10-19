(define (domain MultiRobotRunner)
    (:requirements
        :typing
        :negative-preconditions
        :universal-preconditions
    )

    (:types
        robot gridsquare direction
    )

    (:predicates
        ;; All template information here replicates the single domain - you will need to make substantial adjustments
        ;Planning Robot location for each robot
        (at-agent ?r - robot ?loc - gridsquare)
        ;Robot is on a particular gridsquare (for collision detection)
        (robot-at ?loc - gridsquare)
        ;Agent Robot is rotated a particular way for each robot
        (agent-rotated ?r - robot ?d - direction)
        ;Grid square adjacent in particular direction
        (gridsquare-connected ?from ?to - gridsquare ?d - direction)
        ;Rotation adjacency
        (rotation-adjacent ?from ?to - direction)
        ;Robot has completed its action for this timestep (lockstep)
        (robot-done ?r - robot)
        ;Edge used in current timestep (prevent swapping collisions)
        (edge-used ?from ?to - gridsquare)
    )

    ;The Agent Robot can move if
    ;  - The Agent Robot is at the current location,
    ;  - The Agent Robot is rotated towards the square,
    ;  - There is no Robot at the destination,
    ;  - The Agent Robot is not already at the destination location,
    ;  - The Agent Robot has not already moved this timestep,
    ;  - No other robot is moving in the opposite direction.
    ;Effects: Move the Agent Robot to the destination, mark it as done,
    ;         update occupancy, and mark the edge used.
    (:action moveforward
        :parameters (?r - robot ?from - gridsquare ?to - gridsquare ?d - direction)
        :precondition (and 
            (at-agent ?r ?from)
            (agent-rotated ?r ?d)
            (gridsquare-connected ?from ?to ?d)
            (not (robot-done ?r))
            (not (robot-at ?to))
            (not (edge-used ?to ?from))
        )
        :effect (and 
            (not (at-agent ?r ?from))
            (at-agent ?r ?to)
            (not (robot-at ?from))
            (robot-at ?to)
            (robot-done ?r)
            (edge-used ?from ?to)
        )
    )

    ;The Agent Robot can rotate the direction it is currently facing from its old 
    ; direction to a new direction if
    ;  - The Agent Robot is at the Current Rotation,
    ;  - The Destination Rotation is an adjacent rotation to the Current Rotation,
    ;  - The Agent Robot has not already moved this timestep.
    ;Effects: Switch the rotation of the agent to the new rotation and mark it as done.
    (:action rotate
        :parameters (?r - robot ?from - direction ?to - direction)
        :precondition (and 
            (agent-rotated ?r ?from)
            (rotation-adjacent ?from ?to)
            (not (robot-done ?r))
        )
        :effect (and 
            (not (agent-rotated ?r ?from))
            (agent-rotated ?r ?to)
            (robot-done ?r)
        )
    )

    ;A robot may choose to wait for this timestep if
    ;  - The Agent Robot is at a location,
    ;  - The Agent Robot has not already moved this timestep.
    ;Effects: Mark the robot as done and keep occupancy at its current location.
    (:action wait
        :parameters (?r - robot ?loc - gridsquare)
        :precondition (and 
            (at-agent ?r ?loc)
            (not (robot-done ?r))
        )
        :effect (and 
            (robot-done ?r)
            (robot-at ?loc)
        )
    )

    ;Advance to the next synchronous timestep after all robots have acted if
    ;  - All robots have completed their action for this timestep.
    ;Effects: Reset all robot-done flags, all occupancy markers,
    ;         and all edge-used markers for the next timestep.
    (:action advance-time
        :parameters ()
        :precondition (and 
            (forall (?r - robot) (robot-done ?r))
        )
        :effect (and 
            (forall (?r - robot) (not (robot-done ?r)))
            (forall (?loc - gridsquare) (not (robot-at ?loc)))
            (forall (?from - gridsquare)
                (forall (?to - gridsquare)
                    (not (edge-used ?from ?to))
                )
            )
        )
    )
)
