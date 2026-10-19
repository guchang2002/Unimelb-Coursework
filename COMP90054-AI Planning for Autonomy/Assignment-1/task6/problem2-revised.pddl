(define (problem p2-multi-agent-nonoptimal)
    (:domain MultiRobotRunner)

    (:objects
        robot1 robot2 - robot
        cell-west cell-centre cell-east cell-south cell-north - gridsquare
        north east south west - direction
    )

    (:init
        ;; Each robot has a two-move single-agent shortest path through
        ;; cell-centre. If both take their individually optimal first move,
        ;; they would both enter cell-centre in the same timestep.
        (at-agent robot1 cell-west)
        (agent-rotated robot1 east)

        (at-agent robot2 cell-south)
        (agent-rotated robot2 north)

        ;; Horizontal route for robot1.
        (gridsquare-connected cell-west cell-centre east)
        (gridsquare-connected cell-centre cell-west west)
        (gridsquare-connected cell-centre cell-east east)
        (gridsquare-connected cell-east cell-centre west)

        ;; Vertical route for robot2.
        (gridsquare-connected cell-south cell-centre north)
        (gridsquare-connected cell-centre cell-south south)
        (gridsquare-connected cell-centre cell-north north)
        (gridsquare-connected cell-north cell-centre south)

        ;; Legal 90-degree rotations.
        (rotation-adjacent north east)
        (rotation-adjacent east south)
        (rotation-adjacent south west)
        (rotation-adjacent west north)
        (rotation-adjacent north west)
        (rotation-adjacent west south)
        (rotation-adjacent south east)
        (rotation-adjacent east north)
    )

    (:goal
        (and
            (at-agent robot1 cell-east)
            (at-agent robot2 cell-north)
        )
    )
)
