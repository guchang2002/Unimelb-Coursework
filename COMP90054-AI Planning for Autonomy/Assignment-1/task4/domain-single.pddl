(define (domain SingleRobotRunner)
(:requirements
    :typing
    :negative-preconditions
)

(:types
    robot gridsquare direction
)

(:predicates
    ;Planning Robot location
    (at-agent ?loc - gridsquare)
    ;Robot is on a particular gridsquare
    (robot-at ?t - gridsquare)
    ;Agent Robot is rotated a particular way
    (agent-rotated ?d - direction)
    ;Grid square adjacent in particular direction
    (gridsquare-connected ?from ?to - gridsquare ?d - direction)
    ;Rotation adjacency
    (rotation-adjacent ?from ?to - direction)
)

;The Agent Robot can move if
;  - The Agent Robot is at the current location,
;  - The Agent Robot is rotated towards the square,
;  - There is no Robot at the destination,
;  - The Agent Robot is not already at the destination location.
;Effects: Move the Agent Robot to the destination.
(:action moveforward
    :parameters (?from - gridsquare ?to - gridsquare ?d - direction)
    :precondition (and 
        (at-agent ?from)
        (agent-rotated ?d)
        (gridsquare-connected ?from ?to ?d)
        (not (robot-at ?to))
    )
    :effect (and 
        (not (at-agent ?from))
        (at-agent ?to)
    )
)

;The Agent Robot can rotate the direction it is currently facing from its old 
; direction to a new direction if
;  - The Agent Robot is at the Current Rotation,
;  - The Destination Rotation is an adjacent rotation to the Current Rotation,
;Effects: Switch the rotation of the agent to the new rotation
(:action rotate
    :parameters (?from - direction ?to - direction)
    :precondition (and 
        (agent-rotated ?from)
        (rotation-adjacent ?from ?to)
    )
    :effect (and 
        (not (agent-rotated ?from))
        (agent-rotated ?to)
    )
)

)
