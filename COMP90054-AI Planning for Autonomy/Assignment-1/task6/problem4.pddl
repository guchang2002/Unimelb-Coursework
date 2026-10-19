;It is recommended that you install the misc-pddl-generators plugin 
;and then use the Network generator to create the graph
(define (problem p4-network)
    (:domain MultiRobotRunner)
    (:objects
        robot1 robot2 - robot
        square1 square2 square3 square4 square5 - gridsquare
        north east south west - direction
    )
    (:init
        ; Locations of Robots
        
        ; Robot rotations
        
        ; Gridsquare connections (Insert -> Network)
        
        ; Directions
    )
    (:goal (and
        ; Final Task Location(s)
    ))
)