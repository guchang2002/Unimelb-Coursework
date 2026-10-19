(define (problem p3-vertex-and-edge-collisions)
    (:domain MultiRobotRunner)

    (:objects
        robot1 robot2 - robot
        cell-left cell-centre cell-right cell-pocket - gridsquare
        north east south west - direction
    )

    (:init
        ;; The robots must swap sides of a narrow corridor.
        (at-agent robot1 cell-left)
        (agent-rotated robot1 east)

        (at-agent robot2 cell-right)
        (agent-rotated robot2 west)

        ;; Main corridor: left -- centre -- right
        (gridsquare-connected cell-left cell-centre east)
        (gridsquare-connected cell-centre cell-left west)
        (gridsquare-connected cell-centre cell-right east)
        (gridsquare-connected cell-right cell-centre west)

        ;; A side pocket above the centre makes a collision-free swap possible.
        (gridsquare-connected cell-centre cell-pocket north)
        (gridsquare-connected cell-pocket cell-centre south)

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
            (at-agent robot1 cell-right)
            (at-agent robot2 cell-left)
        )
    )
)
