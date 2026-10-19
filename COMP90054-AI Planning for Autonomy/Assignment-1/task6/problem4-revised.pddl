(define (problem p4-four-agent-lockstep-cycle)
    (:domain MultiRobotRunner)

    (:objects
        robot1 robot2 robot3 robot4 - robot
        square1 square2 square3 square4 - gridsquare
        north east south west - direction
    )

    (:init
        ;; Four robots occupy a 2x2 cycle:
        ;;
        ;;   square1 ---- square2
        ;;      |            |
        ;;      |            |
        ;;   square4 ---- square3
        ;;
        ;; Every robot is already facing the next square clockwise.
        (at-agent robot1 square1)
        (agent-rotated robot1 east)

        (at-agent robot2 square2)
        (agent-rotated robot2 south)

        (at-agent robot3 square3)
        (agent-rotated robot3 west)

        (at-agent robot4 square4)
        (agent-rotated robot4 north)

        ;; 2x2 cycle connections.
        (gridsquare-connected square1 square2 east)
        (gridsquare-connected square2 square1 west)

        (gridsquare-connected square2 square3 south)
        (gridsquare-connected square3 square2 north)

        (gridsquare-connected square3 square4 west)
        (gridsquare-connected square4 square3 east)

        (gridsquare-connected square4 square1 north)
        (gridsquare-connected square1 square4 south)

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
            (at-agent robot1 square2)
            (at-agent robot2 square3)
            (at-agent robot3 square4)
            (at-agent robot4 square1)
        )
    )
)
