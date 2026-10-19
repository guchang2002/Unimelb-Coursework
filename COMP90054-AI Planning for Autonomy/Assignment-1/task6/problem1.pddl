(define (problem p1-enhanced)
    (:domain SingleRobotRunner)
    (:objects
        robot1 - robot
        square1 square2 square3 square4 square5 square6 square7 square8 - gridsquare
        north east south west - direction
    )
    (:init
        ; set a wrong direction
        (at-agent square1)
        (agent-rotated east)
        

        (robot-at square4)
        (robot-at square8)          ; barriers
        

        ; graph
        (gridsquare-connected square1 square2 east)
        (gridsquare-connected square2 square1 west)
        (gridsquare-connected square2 square3 east)
        (gridsquare-connected square3 square2 west)
        (gridsquare-connected square2 square4 south)   ; occupied
        (gridsquare-connected square4 square2 north)
        (gridsquare-connected square3 square6 east)
        (gridsquare-connected square6 square3 west)
        (gridsquare-connected square6 square7 south)
        (gridsquare-connected square7 square6 north)
        (gridsquare-connected square5 square7 east)
        (gridsquare-connected square7 square5 west)
        
        ; wrong paths
        (gridsquare-connected square3 square8 south)   
        (gridsquare-connected square8 square3 north)
        
        ; rotation
        (rotation-adjacent north east)
        (rotation-adjacent east south)
        (rotation-adjacent south west)
        (rotation-adjacent west north)
        (rotation-adjacent north west)
        (rotation-adjacent west south)
        (rotation-adjacent south east)
        (rotation-adjacent east north)
    )
    (:goal (at-agent square5))
)
