(define (problem p1-single-agent-obstacle)
    (:domain SingleRobotRunner)

    (:objects
        blocker1 - robot
        square1 square2 square3 square4 square5 square6 - gridsquare
        north east south west - direction
    )

    (:init
        ;; The controlled robot starts at square1 facing east.
        (at-agent square1)
        (agent-rotated east)

        ;; square2 is occupied by an immovable robot, so the direct route
        ;; square1 -> square2 -> square3 cannot be used.
        (robot-at square2)

        ;; Top row: square1 -- square2 -- square3
        (gridsquare-connected square1 square2 east)
        (gridsquare-connected square2 square1 west)
        (gridsquare-connected square2 square3 east)
        (gridsquare-connected square3 square2 west)

        ;; Bottom detour: square1 -> square4 -> square5 -> square6 -> square3
        (gridsquare-connected square1 square4 south)
        (gridsquare-connected square4 square1 north)
        (gridsquare-connected square4 square5 east)
        (gridsquare-connected square5 square4 west)
        (gridsquare-connected square5 square6 east)
        (gridsquare-connected square6 square5 west)
        (gridsquare-connected square6 square3 north)
        (gridsquare-connected square3 square6 south)

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
        (at-agent square3)
    )
)
