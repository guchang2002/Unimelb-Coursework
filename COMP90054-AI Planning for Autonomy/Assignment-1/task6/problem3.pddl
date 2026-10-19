(define (problem p3-avoid-collisions)
    (:domain MultiRobotRunner)
    (:objects
        robot1 robot2 - robot
        square1 square2 square3 square4 - gridsquare
        north east south west - direction
    )
    (:init
        (at-agent robot1 square1)
        (at-agent robot2 square4)
        
        (agent-rotated robot1 east)      
        (agent-rotated robot2 north)     
        
        (robot-at square1)
        (robot-at square4)
        
        (gridsquare-connected square1 square2 east)
        (gridsquare-connected square2 square1 west)
        (gridsquare-connected square4 square2 north)
        (gridsquare-connected square2 square4 south)
        
        (gridsquare-connected square2 square3 east)
        (gridsquare-connected square3 square2 west)
        (gridsquare-connected square1 square3 north)
        (gridsquare-connected square3 square1 south)
        
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
            (at-agent robot1 square3)
            (at-agent robot2 square2)
        )
    )
)
