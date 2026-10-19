(define (problem p2-nonoptimal-path)
    (:domain MultiRobotRunner)
    (:objects
        robot1 robot2 - robot
        square1 square2 square3 square4 square5 square6 - gridsquare
        north east south west - direction
    )
    (:init
        (at-agent robot1 square1)        ; robot1 从 square1 出发
        (at-agent robot2 square2)        ; robot2 挡住 square2
        

        (agent-rotated robot1 east)
        (agent-rotated robot2 west)
        
  
        (robot-at square1)
        (robot-at square2)
        
   
        (gridsquare-connected square1 square2 east)
        (gridsquare-connected square2 square1 west)
        (gridsquare-connected square2 square3 east)
        (gridsquare-connected square3 square2 west)
        (gridsquare-connected square3 square4 east)
        (gridsquare-connected square4 square3 west)
        
        (gridsquare-connected square1 square5 south)
        (gridsquare-connected square5 square1 north)
        (gridsquare-connected square5 square6 east)
        (gridsquare-connected square6 square5 west)
        (gridsquare-connected square6 square4 north)
        (gridsquare-connected square4 square6 south)
        
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
            (at-agent robot1 square4)
            (at-agent robot2 square2)     
        )
    )
)
