(define (domain MultiRobotRunner)
    (:requirements
        :adl
        :typing
    )

    (:types
        robot gridsquare direction
    )

    (:predicates
        ;; Current state of each robot. These predicates are only changed
        ;; when advance-time commits the whole synchronous timestep.
        (at-agent ?r - robot ?loc - gridsquare)
        (agent-rotated ?r - robot ?d - direction)

        ;; Static map / orientation information.
        (gridsquare-connected ?from ?to - gridsquare ?d - direction)
        (rotation-adjacent ?from ?to - direction)

        ;; A robot may choose exactly one action in each timestep.
        (robot-done ?r - robot)

        ;; Reservations for the NEXT state of the current timestep.
        ;; reserved prevents two robots from ending the timestep in the
        ;; same grid square (vertex collision).
        (reserved ?loc - gridsquare)

        ;; Records directed moves selected in this timestep.
        ;; Checking the reverse edge prevents swapping / edge collisions.
        (edge-used ?from ?to - gridsquare)

        ;; Deferred effects. Choosing an action records an intent; the
        ;; robot's real position/orientation is not changed until advance-time.
        (move-intent ?r - robot ?from ?to - gridsquare)
        (rotate-intent ?r - robot ?from ?to - direction)
    )

    ;; Choose a forward move for this timestep.
    ;;
    ;; IMPORTANT: We do NOT require the destination to be empty in the
    ;; current state. This intentionally permits following and cycle moves:
    ;; another robot may currently occupy ?to as long as that robot also
    ;; leaves during this same timestep.
    ;;
    ;; Collision prevention:
    ;;   - (not (reserved ?to)) prevents vertex collisions.
    ;;   - (not (edge-used ?to ?from)) prevents swapping collisions.
    (:action moveforward
        :parameters
            (?r - robot
             ?from - gridsquare
             ?to - gridsquare
             ?d - direction)
        :precondition (and
            (at-agent ?r ?from)
            (agent-rotated ?r ?d)
            (gridsquare-connected ?from ?to ?d)
            (not (robot-done ?r))
            (not (reserved ?to))
            (not (edge-used ?to ?from))
        )
        :effect (and
            (move-intent ?r ?from ?to)
            (reserved ?to)
            (edge-used ?from ?to)
            (robot-done ?r)
        )
    )

    ;; Choose a 90-degree rotation for this timestep.
    ;; A rotating robot stays in its current square, so that square must be
    ;; reserved as its destination for the next state.
    (:action rotate
        :parameters
            (?r - robot
             ?loc - gridsquare
             ?from - direction
             ?to - direction)
        :precondition (and
            (at-agent ?r ?loc)
            (agent-rotated ?r ?from)
            (rotation-adjacent ?from ?to)
            (not (robot-done ?r))
            (not (reserved ?loc))
        )
        :effect (and
            (rotate-intent ?r ?from ?to)
            (reserved ?loc)
            (robot-done ?r)
        )
    )

    ;; Choose to wait for this timestep.
    ;; Waiting leaves the robot in the same square, so that square is
    ;; reserved in the next state.
    (:action wait
        :parameters
            (?r - robot
             ?loc - gridsquare)
        :precondition (and
            (at-agent ?r ?loc)
            (not (robot-done ?r))
            (not (reserved ?loc))
        )
        :effect (and
            (reserved ?loc)
            (robot-done ?r)
        )
    )

    ;; Commit one synchronous timestep.
    ;;
    ;; This action is only available after EVERY robot has selected exactly
    ;; one action. All recorded move/rotation intents are then applied in one
    ;; PDDL action, giving lockstep semantics rather than sequential movement.
    ;;
    ;; After the commit, all temporary reservations/intents are cleared so
    ;; the next timestep can be planned from the new joint state.
    (:action advance-time
        :parameters ()
        :precondition (and
            (forall (?r - robot)
                (robot-done ?r)
            )
        )
        :effect (and
            ;; Apply every selected move simultaneously.
            (forall
                (?r - robot ?from ?to - gridsquare)
                (when
                    (move-intent ?r ?from ?to)
                    (and
                        (not (at-agent ?r ?from))
                        (at-agent ?r ?to)
                    )
                )
            )

            ;; Apply every selected rotation simultaneously.
            (forall
                (?r - robot ?from ?to - direction)
                (when
                    (rotate-intent ?r ?from ?to)
                    (and
                        (not (agent-rotated ?r ?from))
                        (agent-rotated ?r ?to)
                    )
                )
            )

            ;; Reset per-timestep bookkeeping.
            (forall (?r - robot)
                (not (robot-done ?r))
            )

            (forall (?loc - gridsquare)
                (not (reserved ?loc))
            )

            (forall (?from ?to - gridsquare)
                (not (edge-used ?from ?to))
            )

            (forall (?r - robot ?from ?to - gridsquare)
                (not (move-intent ?r ?from ?to))
            )

            (forall (?r - robot ?from ?to - direction)
                (not (rotate-intent ?r ?from ?to))
            )
        )
    )
)
