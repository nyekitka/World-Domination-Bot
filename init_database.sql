DO $$
BEGIN

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'gamestatus') THEN
        CREATE TYPE gamestatus AS ENUM (
            'Waiting',
            'Negotiations',
            'Meeting',
            'Round 1',
            'Round 2',
            'Round 3',
            'Round 4',
            'Round 5',
            'Round 6',
            'Ended'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'messagetype') THEN
        CREATE TYPE messagetype AS ENUM (
            'City',
            'Meteorites',
            'Sanctions',
            'Eco',
            'Negotiations',
            'Attack'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'typeoforder') THEN
        CREATE TYPE typeoforder AS ENUM (
            'Attack',
            'Develop',
            'Shield',
            'Create Meteorites',
            'Eco boost',
            'Sanctions',
            'Invent'
        );
    END IF;


    CREATE OR REPLACE PROCEDURE attack(IN integer, IN integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE is_attacked BOOL;
                meteorites_num INT;
                planet_id INT;
                nround INT;
        BEGIN
            SELECT planetid INTO planet_id FROM City WHERE id=$2;
            IF planet_id = $1 THEN
                RAISE 'AYC' USING ERRCODE='P0003';
            END IF;
            SELECT g.round INTO nround FROM Game g JOIN Planet p ON g.id=p.gameid WHERE p.id=$1;
            SELECT meteorites INTO meteorites_num FROM Planet WHERE id=$1;
            is_attacked := EXISTS(SELECT * FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Attack' AND round=nround);
            IF NOT is_attacked AND meteorites_num > 0 THEN
                UPDATE Planet SET meteorites=meteorites-1 WHERE id=$1;
                INSERT INTO Orders(round, action, planetid, argument) VALUES (nround, 'Attack', $1, $2);
            ELSIF is_attacked THEN
                UPDATE Planet SET meteorites=meteorites+1 WHERE id=$1;
                DELETE FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Attack' AND round=nround;
            ELSE
                RAISE EXCEPTION 'NER' USING ERRCODE='P0004';
            END IF;
        END;
    $_$;

    CREATE TABLE IF NOT EXISTS game (
        id serial NOT NULL,
        status gamestatus DEFAULT 'Waiting'::gamestatus NOT NULL,
        planets integer NOT NULL,
        ecorate integer DEFAULT 95 NOT NULL,
        round integer,
        PRIMARY KEY(id),
        CONSTRAINT partlynotnullforround CHECK (((status <> 'Negotiations'::gamestatus) OR (round <> NULL::integer)))
    );


    CREATE TABLE IF NOT EXISTS "User" (
        tgid bigint NOT NULL,
        gameid integer REFERENCES game(id),
        PRIMARY KEY(tgid)
    );


    CREATE TABLE IF NOT EXISTS admins (
        tgid bigint NOT NULL,
        gameid integer REFERENCES game(id),
        PRIMARY KEY(tgid)
    );

    CREATE TABLE IF NOT EXISTS planet (
        id serial NOT NULL,
        name character varying(32) NOT NULL,
        gameid integer NOT NULL REFERENCES game(id),
        balance integer DEFAULT 1000 NOT NULL,
        meteorites integer DEFAULT 0 NOT NULL,
        isinvented boolean DEFAULT false NOT NULL,
        ownerid bigint REFERENCES "User"(tgid),
        PRIMARY KEY(id)
    );

    CREATE TABLE IF NOT EXISTS city (
        id serial NOT NULL,
        name character varying(32) NOT NULL,
        planetid integer NOT NULL REFERENCES planet(id),
        isshielded boolean DEFAULT false NOT NULL,
        development integer DEFAULT 60 NOT NULL,
        PRIMARY KEY(id)
    );

    CREATE TABLE IF NOT EXISTS infomessages (
        id bigint NOT NULL,
        planetid integer NOT NULL REFERENCES planet(id),
        mtype messagetype NOT NULL,
        PRIMARY KEY(id)
    );

    CREATE TABLE IF NOT EXISTS orders (
        action typeoforder NOT NULL,
        planetid integer NOT NULL REFERENCES planet(id),
        argument integer,
        round integer NOT NULL
    );

    CREATE TABLE IF NOT EXISTS planetmessages (
        ownerid integer NOT NULL REFERENCES planet(id),
        planetid integer NOT NULL REFERENCES planet(id),
        messageid bigint NOT NULL,
        mtype messagetype NOT NULL
    );

    CREATE TABLE IF NOT EXISTS sanctions (
        gameid integer NOT NULL REFERENCES game(id),
        planetfrom integer NOT NULL REFERENCES planet(id),
        planetto integer NOT NULL REFERENCES planet(id)
    );

    CREATE OR REPLACE FUNCTION negotiationsgamestatechecker(integer) RETURNS boolean
        LANGUAGE sql
        RETURN ($1 IN (SELECT p.id FROM (planet p JOIN game g ON ((p.gameid = g.id))) WHERE (g.status = 'Negotiations'::gamestatus)));


    CREATE TABLE IF NOT EXISTS negotiations (
        gameid integer NOT NULL REFERENCES game(id),
        planetfrom integer NOT NULL REFERENCES planet(id),
        planetto integer NOT NULL REFERENCES planet(id),
        CONSTRAINT gamestatechecker CHECK (negotiationsgamestatechecker(planetto)),
        PRIMARY KEY (gameid, planetfrom, planetto)
    );

    CREATE OR REPLACE FUNCTION bilateralnegotiationschecker(integer, integer) RETURNS boolean
        LANGUAGE sql
        RETURN (EXISTS (SELECT negotiations.gameid, negotiations.planetfrom, negotiations.planetto FROM negotiations WHERE ((negotiations.planetfrom = $1) AND (negotiations.planetto = $2))));

    CREATE OR REPLACE PROCEDURE build_shield(IN integer, IN integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE is_shielded BOOL;
                is_ordered BOOL;
                real_planet INT;
                balance_ INT;
                nround INT;
        BEGIN
            SELECT planetid INTO real_planet FROM City WHERE id=$2;
            SELECT isshielded INTO is_shielded FROM City WHERE id=$2;
            SELECT g.round INTO nround FROM Game g JOIN Planet p ON g.id=p.gameid WHERE p.id=$1;
            is_ordered := EXISTS(SELECT * FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Shield' AND round=nround);
            SELECT balance INTO balance_ FROM Planet WHERE id=$1;
            IF real_planet <> $1 THEN
                RAISE EXCEPTION 'DNY' USING ERRCODE='P0005';
            END IF;
            IF balance_ >= 300 AND NOT is_shielded AND NOT is_ordered THEN
                UPDATE Planet SET balance=balance-300 WHERE id=$1;
                INSERT INTO Orders(round, action, planetid, argument) VALUES (nround, 'Shield', $1, $2);
            ELSIF is_ordered THEN
                UPDATE Planet SET balance=balance+300 WHERE id=$1;
                DELETE FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Shield' AND round=nround;
            ELSIF is_shielded THEN
                RAISE EXCEPTION 'CAS' USING ERRCODE='P0006';
            ELSE
                RAISE EXCEPTION 'NEM' USING ERRCODE='P0007';
            END IF;
        END;
    $_$;

    CREATE OR REPLACE PROCEDURE create_meteorites(IN integer, IN integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE is_invented BOOL;
                created_num INT;
                balance_ INT;
                nround INT;
        BEGIN
            SELECT balance, isinvented INTO balance_, is_invented FROM Planet WHERE id=$1;
            SELECT g.round INTO nround FROM Game g JOIN Planet p ON g.id=p.gameid WHERE p.id=$1;
            SELECT COALESCE((SELECT argument FROM Orders WHERE planetid=$1 AND action='Create Meteorites' AND round=nround), 0) INTO created_num;
            IF is_invented AND balance_ + 150 * created_num >= 150 * $2 THEN
                UPDATE Planet SET balance = balance + 150 * (created_num - $2) WHERE id=$1;
                IF created_num = 0 THEN
                    INSERT INTO Orders(round, planetid, action, argument) VALUES (nround, $1, 'Create Meteorites', $2);
                ELSE
                    UPDATE Orders SET argument = $2 WHERE planetid=$1 AND action='Create Meteorites' AND round=nround;
                END IF;
            ELSIF NOT is_invented THEN
                RAISE EXCEPTION 'MNI' USING ERRCODE='P0008';
            ELSE
                RAISE EXCEPTION 'NEM' USING ERRCODE='P0007';
            END IF;
        END;
    $_$;


    CREATE OR REPLACE PROCEDURE develop(IN integer, IN integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE is_developed BOOL;
                real_planet INT;
                balance_ INT;
                nround INT;
        BEGIN
            SELECT planetid INTO real_planet FROM City WHERE id=$2;
            SELECT g.round INTO nround FROM Game g JOIN Planet p ON g.id=p.gameid WHERE p.id=$1;
            is_developed := EXISTS(SELECT * FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Develop' AND round=nround);
            SELECT balance INTO balance_ FROM Planet WHERE id=$1;
            IF real_planet <> $1 THEN
                RAISE EXCEPTION 'DVNY' USING ERRCODE='P0009';
            END IF;
            IF balance_ >= 150 AND NOT is_developed THEN
                UPDATE Planet SET balance=balance-150 WHERE id=$1;
                INSERT INTO Orders(round, action, planetid, argument) VALUES (nround, 'Develop', $1, $2);
            ELSIF is_developed THEN
                UPDATE Planet SET balance=balance+150 WHERE id=$1;
                DELETE FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Develop' AND round=nround;
            ELSE
                RAISE EXCEPTION 'NEM' USING ERRCODE='P0007';
            END IF;
        END;
    $_$;


    CREATE OR REPLACE PROCEDURE ecoboost(IN integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE is_boosted BOOL;
                meteors INT;
                nround INT;
        BEGIN
            SELECT g.round INTO nround FROM Game g JOIN Planet p ON g.id=p.gameid WHERE p.id=$1;
            is_boosted := EXISTS(SELECT * FROM Orders WHERE action='Eco boost' AND planetid=$1 AND round=nround);
            SELECT meteorites INTO meteors FROM Planet WHERE id=$1;
            IF meteors > 0 AND NOT is_boosted THEN
                INSERT INTO Orders(round, action, planetid) VALUES (nround, 'Eco boost', $1);
                UPDATE Planet SET meteorites=meteorites-1 WHERE id=$1;
            ELSIF is_boosted THEN
                DELETE FROM Orders WHERE action='Eco boost' AND planetid=$1 AND round=nround;
                UPDATE Planet SET meteorites=meteorites+1 WHERE id=$1;
            ELSE
                RAISE EXCEPTION 'NER' USING ERRCODE='P0010';
            END IF;
        END;
    $_$;


    CREATE OR REPLACE PROCEDURE end_game(IN game_id integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE trash BOOL;
        BEGIN
            UPDATE "User" SET gameid=NULL WHERE gameid=game_id;
            UPDATE Admins SET gameid=NULL WHERE gameid=game_id;
            DELETE FROM Orders WHERE planetid IN (SELECT id FROM Planet WHERE gameid=game_id);
            DELETE FROM InfoMessages WHERE planetid IN (SELECT id FROM Planet WHERE gameid=game_id);
            DELETE FROM PlanetMessages WHERE planetid IN (SELECT id FROM Planet WHERE gameid=game_id);
            DELETE FROM Negotiations WHERE gameid=game_id;
            DELETE FROM Sanctions WHERE gameid=game_id;
            DELETE FROM City WHERE planetid IN (SELECT id FROM Planet WHERE gameid=game_id);
            DELETE FROM Planet WHERE gameid=game_id;
            DELETE FROM Game WHERE id=game_id;
            DROP TABLE delete_planets;
        END;
    $_$;


    CREATE OR REPLACE PROCEDURE end_this_round(IN gameid integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE num_inventors INT;
                num_shielded INT;
                num_attacked INT;
                current_round INT;
                eco_boosts INT;
                meteorites_created INT;
        BEGIN
            
            SELECT round INTO current_round FROM Game WHERE id=$1;
            CREATE TEMPORARY TABLE OurOrders(action typeoforder, planetid INT, argument INT, round INT);
            INSERT INTO OurOrders(action, planetid, argument, round) 
                SELECT o.action, o.planetid, o.argument, o.round FROM Orders o
                JOIN Planet p ON p.id=o.planetid
                WHERE p.gameid=$1;

            
            -- shield cities
            CREATE TEMPORARY TABLE defend_cities (cityid INT);
            INSERT INTO defend_cities (cityid) SELECT c.id FROM OurOrders o 
                JOIN City c ON c.id = o.argument 
                WHERE action='Shield' AND round=current_round;
            SELECT COUNT(*) INTO num_shielded FROM defend_cities;
            UPDATE City SET isshielded=TRUE WHERE id IN (SELECT * FROM defend_cities);
            UPDATE Game SET ecorate=ecorate-2*num_shielded WHERE id=$1;

            -- develop cities
            CREATE TEMPORARY TABLE develop_cities (cityid INT);
            INSERT INTO develop_cities(cityid) 
                SELECT c.id FROM OurOrders o JOIN City c ON c.id = o.argument 
                WHERE action='Develop' AND round=current_round;
            UPDATE City SET development=development+20 WHERE id IN (SELECT * FROM develop_cities);

            -- attack cities
            SELECT COUNT(1) INTO num_attacked FROM OurOrders WHERE action='Attack';
            CREATE TEMPORARY TABLE attacked_cities(cityid INT, cnt INT);
            CREATE TEMPORARY TABLE twice_attacked_cities(cityid INT, cnt INT);
            INSERT INTO attacked_cities(cityid, cnt) 
                SELECT c.id, COUNT(c.id) AS cnt FROM OurOrders o 
                JOIN City c ON c.id = o.argument
                WHERE o.action = 'Attack' AND round=current_round
                GROUP BY c.id HAVING COUNT(c.id) = 1;
            INSERT INTO twice_attacked_cities(cityid, cnt) 
                SELECT c.id, COUNT(c.id) AS cnt FROM OurOrders o 
                JOIN City c ON c.id = o.argument
                WHERE o.action = 'Attack' AND round=current_round
                GROUP BY c.id HAVING COUNT(c.id) > 1;
            UPDATE City SET isshielded=FALSE, development=0 WHERE id IN (SELECT cityid FROM twice_attacked_cities);
            UPDATE City SET development=0 WHERE id IN (SELECT cityid FROM attacked_cities) AND NOT isshielded;
            UPDATE City SET isshielded=FALSE WHERE id IN (SELECT cityid FROM attacked_cities) AND isshielded;
            UPDATE Game SET ecorate=ecorate-2*num_attacked WHERE id=$1;

            -- sanctions
            DELETE FROM Sanctions WHERE Sanctions.gameid=$1;
            INSERT INTO Sanctions(gameid, planetfrom, planetto) 
                SELECT $1, planetid, argument FROM OurOrders 
                WHERE action='Sanctions' AND round=current_round;

            -- eco boost
            SELECT COUNT(1) INTO eco_boosts FROM OurOrders 
                WHERE action='Eco boost' AND round=current_round;
            UPDATE Game SET ecorate = ecorate + eco_boosts*20 WHERE id=$1;

            -- create meteorites
            CREATE TEMPORARY TABLE meteorites_planets(planetid INT, argument INT);
            INSERT INTO meteorites_planets(planetid, argument) 
                SELECT planetid, argument FROM OurOrders 
                WHERE action='Create Meteorites' AND round=current_round;
            SELECT COALESCE(SUM(argument), 0) INTO meteorites_created FROM meteorites_planets;
            UPDATE Planet SET meteorites = meteorites + m.argument FROM meteorites_planets m WHERE m.planetid = id;
            UPDATE Game SET ecorate=ecorate-meteorites_created * 2 WHERE id=$1;

            -- invent
            CREATE TEMPORARY TABLE inventors(planetid INT);
            INSERT INTO inventors(planetid) SELECT planetid FROM OurOrders WHERE action='Invent' AND round=current_round;
            SELECT COUNT(1) INTO num_inventors FROM inventors;
            UPDATE Planet SET isinvented = TRUE WHERE id IN (SELECT * FROM inventors);
            UPDATE Game SET ecorate=ecorate - 2 * num_inventors WHERE id=$1;

            -- after updates
            UPDATE Game SET ecorate=GREATEST(5, LEAST(ecorate, 100)), status='Meeting' WHERE id=$1;
            DELETE FROM Negotiations WHERE Negotiations.gameid=$1;

            -- why the hell should I drop the temporary tables
            DROP TABLE OurOrders;
            DROP TABLE defend_cities;
            DROP TABLE develop_cities;
            DROP TABLE attacked_cities;
            DROP TABLE twice_attacked_cities;
            DROP TABLE meteorites_planets;
            DROP TABLE inventors;
        END;
    $_$;


    CREATE OR REPLACE PROCEDURE invent(IN integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE balance_ INT;
                is_invented BOOL;
                is_ordered BOOL;
                game_id INT;
                nround INT;
        BEGIN
            SELECT p.balance, p.isinvented, p.gameid INTO balance_, is_invented, game_id FROM Planet AS p WHERE id = $1;
            SELECT round INTO nround FROM Game WHERE id=game_id;
            is_ordered := EXISTS(SELECT * FROM Orders WHERE planetid=$1 AND action='Invent' AND round=nround);
            IF balance_ >= 500 AND NOT is_invented AND NOT is_ordered THEN
                UPDATE Planet SET balance=balance-500 WHERE id=$1;
                INSERT INTO Orders(action, planetid, round) VALUES ('Invent', $1, nround);
            ELSIF is_ordered THEN
                UPDATE Planet SET balance=balance+500 WHERE id=$1;
                DELETE FROM Orders WHERE planetid=$1 AND action='Invent' AND round=nround;
            ELSIF is_invented THEN
                RAISE EXCEPTION 'ALI' USING ERRCODE='P0011';
            ELSE
                RAISE EXCEPTION 'NEM' USING ERRCODE='P0007';
            END IF;
        END;
    $_$;


    CREATE OR REPLACE PROCEDURE join_admin(IN admin_id bigint, IN game_id integer)
        LANGUAGE plpgsql
        AS $_$
    DECLARE is_entered BOOL;
        BEGIN
            SELECT EXISTS(SELECT * FROM Admins WHERE tgid=admin_id AND gameid IS NOT NULL) INTO is_entered;
            IF is_entered THEN
                RAISE EXCEPTION 'AIG' USING ERRCODE='P0002';
            ELSE
                UPDATE Admins SET gameid=game_id WHERE tgid=admin_id;
            END IF;
        END;
    $_$;


    CREATE OR REPLACE PROCEDURE join_user(IN user_id bigint, IN game_id integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE isingame BOOL;
                hasplanet BOOL;
                ingame INT;
                planets_num INT;
                freeplanets INT;
                game_status gamestatus;
        BEGIN
            isingame := EXISTS(SELECT * FROM "User" WHERE tgid=user_id AND gameid=game_id);
            SELECT planets INTO planets_num FROM Game WHERE id=game_id;
            hasplanet := EXISTS(SELECT * FROM Planet WHERE ownerid=user_id AND gameid=game_id);
            SELECT COUNT(*) INTO ingame FROM "User" WHERE gameid=game_id;
            IF isingame THEN
                RAISE EXCEPTION 'PAL' USING ERRCODE='P0002';
            ELSIF ingame = planets_num THEN
                RAISE EXCEPTION 'LIF' USING ERRCODE='P0016';
            ELSE
                IF NOT hasplanet THEN
                    SELECT COUNT(*) INTO freeplanets FROM Planet WHERE gameid=game_id AND ownerid IS NULL;
                    IF freeplanets = 0 THEN
                        RAISE EXCEPTION 'NFP' USING ERRCODE='P0017';
                    ELSE
                        UPDATE "User" SET gameid=game_id WHERE tgid=user_id;
                        UPDATE Planet SET ownerid=user_id WHERE id IN (
                            SELECT id FROM Planet WHERE ownerid IS NULL AND gameid=game_id
                            ORDER BY id LIMIT 1
                        );
                    END IF;
                ELSE
                    UPDATE "User" SET gameid=game_id WHERE tgid=user_id;
                END IF;
            END IF;
        END;
    $_$;


    CREATE OR REPLACE PROCEDURE kick_admin(IN tgid bigint)
        LANGUAGE plpgsql
        AS $_$DECLARE isingame BOOL;
    BEGIN
        isingame := EXISTS(SELECT * FROM Admins WHERE Admins.tgid=$1 AND gameid IS NOT NULL);
        IF NOT isingame THEN
            RAISE EXCEPTION 'ANL' USING ERRCODE='P0013';
        ELSE
            UPDATE Admins SET gameid=NULL WHERE Admins.tgid=$1;
        END IF;
    END;$_$;

    CREATE OR REPLACE PROCEDURE kick_user(IN user_id bigint)
        LANGUAGE plpgsql
        AS $_$
        DECLARE game_id INT;
                status_game gamestatus;
        BEGIN
            SELECT gameid INTO game_id FROM "User" WHERE tgid=user_id;
            IF game_id IS NULL THEN
                RAISE EXCEPTION 'PNL' USING ERRCODE='P0013';
            ELSE
                SELECT status INTO status_game FROM Game WHERE id=game_id;
                IF status_game = 'Waiting' THEN
                    UPDATE Planet SET ownerid=NULL WHERE ownerid=user_id;
                END IF;
                UPDATE "User" SET gameid=NULL WHERE tgid=user_id;
            END IF;
        END;
    $_$;

    CREATE OR REPLACE FUNCTION negotiationsbusinesschecker(integer) RETURNS boolean
        LANGUAGE sql
        RETURN (EXISTS (SELECT negotiations.gameid, negotiations.planetfrom, negotiations.planetto FROM negotiations WHERE (negotiations.planetto = $1)));


    CREATE OR REPLACE FUNCTION planet_income(integer) RETURNS numeric
        LANGUAGE plpgsql
        AS $_$
    DECLARE sanc_count INT:= (SELECT COUNT(1) FROM Sanctions AS s WHERE s.PlanetTo = $1);
            coef NUMERIC(3, 2) := 1 - 0.1*sanc_count;
    BEGIN
    RETURN (SELECT SUM(income)*coef FROM (SELECT 3*rate_of_life_in_city(c.id) AS income FROM City c WHERE planetid=$1) AS sq);
    END;
    $_$;


    CREATE OR REPLACE FUNCTION rate_of_life_in_city(integer) RETURNS numeric
        LANGUAGE sql
        RETURN (SELECT ((city.development * game.ecorate) / 100) FROM ((city JOIN planet ON ((city.planetid = planet.id))) JOIN game ON ((planet.gameid = game.id))) WHERE (city.id = $1));


    CREATE OR REPLACE FUNCTION rate_of_life_in_planet(integer) RETURNS numeric
        LANGUAGE sql
        RETURN (SELECT (avg((city.development * game.ecorate)) / (100)::numeric) AS avg FROM ((city JOIN planet ON ((city.planetid = planet.id))) JOIN game ON ((planet.gameid = game.id))) GROUP BY planet.id HAVING (planet.id = $1));


    CREATE OR REPLACE PROCEDURE send_sanctions(IN integer, IN integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE is_sent BOOL;
                cur_round INT;
                game INT;
        BEGIN
            SELECT t.gameid INTO game FROM Planet t WHERE id=$1;
            SELECT t.round INTO cur_round FROM Game t WHERE id=game;
            is_sent := EXISTS(SELECT * FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Sanctions' AND round=cur_round);
            IF is_sent THEN
                DELETE FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Sanctions' AND round=cur_round;
            ELSE
                INSERT INTO Orders (round, action, planetid, argument) VALUES (cur_round, 'Sanctions', $1, $2);
            END IF;
        END;
    $_$;

    CREATE OR REPLACE PROCEDURE start_new_round(IN gameid integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE gstatus gamestatus;
                active_players INT;
                all_players INT;
        BEGIN
            SELECT status INTO gstatus FROM Game WHERE id=$1;
            SELECT COUNT(tgid) INTO active_players FROM "User" u WHERE u.gameid=$1;
            SELECT planets INTO all_players FROM Game WHERE id=$1;
            IF active_players < all_players THEN
                RAISE EXCEPTION 'NEP' USING ERRCODE='P0014';
            END IF;
            IF gstatus = 'Meeting' THEN
                UPDATE Planet SET balance=balance+planet_income(id) WHERE Planet.gameid=$1;
            END IF;
            IF gstatus = 'Negotiations' THEN
                RAISE EXCEPTION 'SRI' USING ERRCODE='P0015';
            ELSE
                UPDATE Game SET round=COALESCE(round, 0) + 1, status='Negotiations' WHERE id=$1;
            END IF;
        END;
    $_$;

    CREATE OR REPLACE PROCEDURE transfer(IN frompl integer, IN topl integer, IN amount integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE balance1 INT;
                gamest gamestatus;
        BEGIN
            IF amount <= 0 THEN
                RAISE EXCEPTION 'NGA' USING ERRCODE='P0018';
            END IF;
            SELECT balance INTO balance1 FROM Planet WHERE id=frompl;
            IF balance1 >= amount THEN
                UPDATE Planet SET balance=balance-amount WHERE id=frompl;
                UPDATE Planet SET balance=balance+amount WHERE id=topl;
            ELSE
                RAISE EXCEPTION 'NEM' USING ERRCODE='P0007';
            END IF;
        END;
    $_$;


    IF NOT EXISTS (
            SELECT 1 FROM pg_constraint 
            WHERE conname = 'bilateralconstraint' 
            AND conrelid = 'negotiations'::regclass
        ) THEN
        ALTER TABLE negotiations
    ADD CONSTRAINT bilateralconstraint CHECK ((NOT bilateralnegotiationschecker(planetto, planetfrom)));
    END IF;

    IF NOT EXISTS (
            SELECT 1 FROM pg_constraint 
            WHERE conname = 'negotiationsbusinessconstraint' 
            AND conrelid = 'negotiations'::regclass
        ) THEN
        ALTER TABLE negotiations
        ADD CONSTRAINT negotiationsbusinessconstraint CHECK ((NOT negotiationsbusinesschecker(planetto)));
    END IF;

END$$;



