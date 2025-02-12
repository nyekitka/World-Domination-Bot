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
            'Round 6'
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

    CREATE TABLE IF NOT EXISTS game (
        id SERIAL NOT NULL,
        status gamestatus DEFAULT 'Waiting'::gamestatus NOT NULL,
        planets integer NOT NULL,
        ecorate integer DEFAULT 95 NOT NULL,
        round integer,
        PRIMARY KEY(id),
        CONSTRAINT partlynotnullforround CHECK (((status <> 'Negotiations'::gamestatus) OR (round <> NULL::integer)))
    );

    CREATE TABLE IF NOT EXISTS "User" (
        tgid BIGINT NOT NULL,
        gameid integer REFERENCES game(id),
        PRIMARY KEY(tgid)
    );

    CREATE TABLE IF NOT EXISTS admins (
        tgid BIGINT NOT NULL,
        gameid integer REFERENCES game(id),
        PRIMARY KEY (tgid)
    );

    CREATE TABLE IF NOT EXISTS planet (
        id SERIAL NOT NULL,
        name character varying(32) NOT NULL,
        gameid integer NOT NULL REFERENCES game(id),
        balance integer DEFAULT 1000 NOT NULL,
        meteorites integer DEFAULT 0 NOT NULL,
        isinvented boolean DEFAULT false NOT NULL,
        ownerid BIGINT REFERENCES "User"(tgid),
        PRIMARY KEY(id)
    );

    CREATE TABLE IF NOT EXISTS city (
        id SERIAL NOT NULL,
        name character varying(32) NOT NULL,
        planetid integer NOT NULL REFERENCES planet(id),
        isshielded boolean DEFAULT false NOT NULL,
        development integer DEFAULT 60 NOT NULL,
        PRIMARY KEY(id)
    );

    CREATE TABLE IF NOT EXISTS orders (
        action typeoforder NOT NULL,
        planetid integer NOT NULL REFERENCES planet(id),
        argument integer
    );

    CREATE TABLE IF NOT EXISTS sanctions (
        gameid integer NOT NULL REFERENCES game(id),
        planetfrom integer NOT NULL REFERENCES planet(id),
        planetto integer NOT NULL REFERENCES planet(id),
        round integer NOT NULL,
        PRIMARY KEY (planetfrom, planetto, round)
    );
    
    CREATE TABLE IF NOT EXISTS negotiations (
        gameid integer NOT NULL REFERENCES game(id),
        planetfrom integer NOT NULL REFERENCES planet(id),
        planetto integer NOT NULL REFERENCES planet(id),
        PRIMARY KEY (gameid, planetfrom, planetto)
    );

    CREATE OR REPLACE FUNCTION negotiationsgamestatechecker(integer) RETURNS boolean
    LANGUAGE sql
    RETURN ($1 IN (SELECT p.id FROM (planet p JOIN game g ON ((p.gameid = g.id))) WHERE (g.status = 'Negotiations'::gamestatus)));

    CREATE OR REPLACE FUNCTION bilateralnegotiationschecker(integer, integer) RETURNS boolean
    LANGUAGE sql
    RETURN (EXISTS (SELECT negotiations.gameid, negotiations.planetfrom, negotiations.planetto FROM negotiations WHERE ((negotiations.planetfrom = $1) AND (negotiations.planetto = $2))));
    
    IF NOT EXISTS (
            SELECT 1 FROM pg_constraint 
            WHERE conname = 'gamestatechecker' 
            AND conrelid = 'negotiations'::regclass
        ) THEN
        ALTER TABLE negotiations
        ADD CONSTRAINT gamestatechecker CHECK (negotiationsgamestatechecker(planetto));
    END IF;

     IF NOT EXISTS (
            SELECT 1 FROM pg_constraint 
            WHERE conname = 'gamestatechecker' 
            AND conrelid = 'negotiations'::regclass
        ) THEN
        ALTER TABLE negotiations
        ADD CONSTRAINT gamestatechecker CHECK (negotiationsgamestatechecker(planetto));
    END IF;

    IF NOT EXISTS (
            SELECT 1 FROM pg_constraint 
            WHERE conname = 'gamestatechecker' 
            AND conrelid = 'negotiations'::regclass
        ) THEN
        ALTER TABLE negotiations
        ADD CONSTRAINT negotiationsbusinessconstraint CHECK ((NOT negotiationsbusinesschecker(planetto)));
    END IF;

    CREATE OR REPLACE PROCEDURE attack(IN integer, IN integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE is_attacked BOOL;
                meteorites_num INT;
                planet_id INT;
        BEGIN
            SELECT planetid INTO planet_id FROM City WHERE id=$2;
            IF planet_id = $1 THEN
                RAISE 'AYC';
            END IF;
            SELECT meteorites INTO meteorites_num FROM Planet WHERE id=$1;
            is_attacked := EXISTS(SELECT * FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Attack');
            IF NOT is_attacked AND meteorites_num > 0 THEN
                UPDATE Planet SET meteorites=meteorites-1 WHERE id=$1;
                INSERT INTO Orders(action, planetid, argument) VALUES ('Attack', $1, $2);
            ELSIF is_attacked THEN
                UPDATE Planet SET meteorites=meteorites+1 WHERE id=$1;
                DELETE FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Attack';
            ELSE
                RAISE EXCEPTION 'NER';
            END IF;
        END;
    $_$;
    
    CREATE OR REPLACE PROCEDURE build_shield(IN integer, IN integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE is_shielded BOOL;
                is_ordered BOOL;
                real_planet INT;
                balance_ INT;
        BEGIN
            SELECT planetid INTO real_planet FROM City WHERE id=$2;
            SELECT isshielded INTO is_shielded FROM City WHERE id=$2;
            is_ordered := EXISTS(SELECT * FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Shield');
            SELECT balance INTO balance_ FROM Planet WHERE id=$1;
            IF real_planet <> $1 THEN
                RAISE EXCEPTION 'DNY';
            END IF;
            IF balance_ >= 300 AND NOT is_shielded AND NOT is_ordered THEN
                UPDATE Planet SET balance=balance-300 WHERE id=$1;
                INSERT INTO Orders(action, planetid, argument) VALUES ('Shield', $1, $2);
            ELSIF is_ordered THEN
                UPDATE Planet SET balance=balance+300 WHERE id=$1;
                DELETE FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Shield';
            ELSIF is_shielded THEN
                RAISE EXCEPTION 'CAS';
            ELSE
                RAISE EXCEPTION 'NEM';
            END IF;
        END;
    $_$;

    CREATE OR REPLACE PROCEDURE create_meteorites(IN integer, IN integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE is_invented BOOL;
                created_num INT;
                balance_ INT;
        BEGIN
            SELECT balance, isinvented INTO balance_, is_invented FROM Planet WHERE id=$1;
            SELECT COALESCE((SELECT argument FROM Orders WHERE planetid=$1 AND action='Create Meteorites'), 0) INTO created_num;
            IF is_invented AND balance_ + 150 * created_num >= 150 * $2 THEN
                UPDATE Planet SET balance = balance + 150 * (created_num - $2) WHERE id=$1;
                IF created_num = 0 THEN
                    INSERT INTO Orders(planetid, action, argument) VALUES ($1, 'Create Meteorites', $2);
                ELSE
                    UPDATE Orders SET argument = $2 WHERE planetid=$1 AND action='Create Meteorites';
                END IF;
            ELSIF NOT is_invented THEN
                RAISE EXCEPTION 'MNI';
            ELSE
                RAISE EXCEPTION 'NEM';
            END IF;
        END;
    $_$;

    CREATE OR REPLACE PROCEDURE develop(IN integer, IN integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE is_developed BOOL;
                real_planet INT;
                balance_ INT;
        BEGIN
            SELECT planetid INTO real_planet FROM City WHERE id=$2;
            is_developed := EXISTS(SELECT * FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Develop');
            SELECT balance INTO balance_ FROM Planet WHERE id=$1;
            IF real_planet <> $1 THEN
                RAISE EXCEPTION 'DNY';
            END IF;
            IF balance_ >= 150 AND NOT is_developed THEN
                UPDATE Planet SET balance=balance-150 WHERE id=$1;
                INSERT INTO Orders(action, planetid, argument) VALUES ('Develop', $1, $2);
            ELSIF is_developed THEN
                UPDATE Planet SET balance=balance+150 WHERE id=$1;
                DELETE FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Develop';
            ELSE
                RAISE EXCEPTION 'NEM';
            END IF;
        END;
    $_$;

    CREATE OR REPLACE PROCEDURE ecoboost(IN integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE is_boosted BOOL;
                meteors INT;
        BEGIN
            is_boosted := EXISTS(SELECT * FROM Orders WHERE action='Eco boost' AND planetid=$1);
            SELECT meteorites INTO meteors FROM Planet WHERE id=$1;
            IF meteors > 0 AND NOT is_boosted THEN
                INSERT INTO Orders(action, planetid) VALUES ('Eco boost', $1);
                UPDATE Planet SET meteorites=meteorites-1 WHERE id=$1;
            ELSIF is_boosted THEN
                DELETE FROM Orders WHERE action='Eco boost' AND planetid=$1;
                UPDATE Planet SET meteorites=meteorites+1 WHERE id=$1;
            ELSE
                RAISE EXCEPTION 'NER';
            END IF;
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
            
            SELECT round INTO current_round FROM Game WHERE gameid=$1;

            -- shield cities
            CREATE TEMP TABLE defend_cities (cityid INT);
            INSERT INTO defend_cities (cityid) SELECT c.id FROM Orders o JOIN City c ON c.id = o.argument WHERE action='Shield';
            SELECT COUNT(*) INTO num_shielded FROM defend_cities;
            UPDATE City SET isshielded=TRUE WHERE id IN (SELECT * FROM defend_cities);
            UPDATE Game SET ecorate=ecorate-2*num_shielded WHERE id=gameid;

            -- develop cities
            CREATE TEMP TABLE develop_cities (cityid INT);
            INSERT INTO develop_cities(cityid) SELECT c.id FROM Orders o JOIN City c ON c.id = o.argument WHERE action='Develop';
            UPDATE City SET development=development+20 WHERE id IN (SELECT * FROM develop_cities);

            -- attack cities
            SELECT COUNT(1) INTO num_attacked FROM Orders WHERE action='Attack';
            CREATE TEMP TABLE attacked_cities(cityid INT, cnt INT);
            CREATE TEMP TABLE twice_attacked_cities(cityid INT, cnt INT);
            INSERT INTO attacked_cities(cityid, cnt) SELECT c.id, COUNT(c.id) AS cnt FROM Orders o 
                JOIN City c ON c.id = o.argument 
                GROUP BY c.id, o.action HAVING o.action = 'Attack' AND COUNT(c.id) = 1;
            INSERT INTO twice_attacked_cities(cityid, cnt) SELECT c.id, COUNT(c.id) AS cnt FROM Orders o 
                JOIN City c ON c.id = o.argument 
                GROUP BY c.id, o.action HAVING o.action = 'Attack' AND COUNT(c.id) > 1;
            UPDATE City SET isshielded=FALSE, development=0 WHERE id IN (SELECT cityid FROM twice_attacked_cities);
            UPDATE City SET isshielded=FALSE WHERE id IN (SELECT cityid FROM attacked_cities) AND isshielded;
            UPDATE City SET development=0 WHERE id IN (SELECT cityid FROM attacked_cities) AND NOT isshielded;
            UPDATE Game SET ecorate=ecorate-2*num_attacked WHERE id=$1;

            -- sanctions
            INSERT INTO Sanctions(gameid, planetfrom, planetto, round) SELECT $1, planetid, argument, current_round FROM Orders WHERE action='Sanctions';

            -- eco boost
            SELECT COUNT(1) INTO eco_boosts FROM Orders WHERE action='Eco boost';
            UPDATE Game SET ecorate = ecorate + eco_boosts*20 WHERE id=$1;

            -- create meteorites
            CREATE TEMP TABLE meteorites_planets(planetid INT, argument INT);
            INSERT INTO meteorites_planets(planetid, argument) SELECT planetid, argument FROM Orders 
                WHERE action='Create Meteorites';
            SELECT COALESCE(SUM(argument), 0) INTO meteorites_created FROM meteorites_planets;
            UPDATE Planet SET meteorites = meteorites + m.argument FROM meteorites_planets m WHERE m.planetid = id;
            UPDATE Game SET ecorate=ecorate-meteorites_created * 2 WHERE id=$1;

            -- invent
            CREATE TEMP TABLE inventors(planetid INT);
            INSERT INTO inventors(planetid) SELECT planetid FROM Orders WHERE action='Invent';
            SELECT COUNT(1) INTO num_inventors FROM inventors;
            UPDATE Planet SET isinvented = TRUE WHERE id IN (SELECT * FROM inventors);
            UPDATE Game SET ecorate=ecorate - 2 * num_inventors WHERE id=$1;

            -- after updates
            UPDATE Game SET ecorate=GREATEST(5, LEAST(ecorate, 100)), status='Meeting', round=round+1 WHERE id=$1;
            TRUNCATE TABLE Orders;
            TRUNCATE TABLE Negotiations;
            
        END;
    $_$;

    CREATE OR REPLACE PROCEDURE invent(IN integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE balance_ INT;
                is_invented BOOL;
                is_ordered BOOL;
        BEGIN
            SELECT p.balance, p.isinvented INTO balance_, is_invented FROM Planet AS p WHERE id = $1;
            is_ordered := EXISTS(SELECT * FROM Orders WHERE planetid=$1 AND action='Invent');
            IF balance_ >= 500 AND NOT is_invented AND NOT is_ordered THEN
                UPDATE Planet SET balance=balance-500 WHERE id=$1;
                INSERT INTO Orders(action, planetid) VALUES ('Invent', $1);
            ELSIF is_ordered THEN
                UPDATE Planet SET balance=balance+500 WHERE id=$1;
                DELETE FROM Orders WHERE planetid=$1 AND action='Invent';
            ELSIF is_invented THEN
                RAISE EXCEPTION 'ALI';
            ELSE
                RAISE EXCEPTION 'NEM';
            END IF;
        END;
    $_$;

    CREATE OR REPLACE PROCEDURE join_user(IN userid BIGINT, IN game integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE isingame BOOL;
                free_planet INT;
        BEGIN
            isingame := EXISTS(SELECT * FROM "User" WHERE tgid=$1 AND gameid=$2);
            IF isingame THEN
                RAISE EXCEPTION 'PAL';
            ELSE
                UPDATE "User" SET gameid=$2 WHERE tgid=$1;
                SELECT id INTO free_planet FROM Planet WHERE gameid=$2 AND ownerid IS NULL LIMIT 1;
                UPDATE Planet SET ownerid=$1 WHERE id=free_planet;
            END IF;
        END;
    $_$;

    CREATE OR REPLACE PROCEDURE join_admin(IN adminid BIGINT, IN game integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE isingame BOOL;
        BEGIN
            isingame := EXISTS(SELECT * FROM admins WHERE tgid=$1 AND gameid=$2);
            IF isingame THEN
                RAISE EXCEPTION 'PAL';
            ELSE
                UPDATE admins SET gameid=$2 WHERE tgid=$1;
            END IF;
        END;
    $_$;

    CREATE OR REPLACE PROCEDURE kick_user(IN userid BIGINT)
        LANGUAGE plpgsql
        AS $_$
        DECLARE isingame BOOL;
        BEGIN
            isingame := EXISTS(SELECT * FROM "User" WHERE tgid=$1 AND gameid IS NOT NULL);
            IF NOT isingame THEN
                RAISE EXCEPTION 'PNL';
            ELSE
                UPDATE "User" SET gameid=NULL WHERE tgid=$1;
            END IF;
        END;
    $_$;

    CREATE OR REPLACE FUNCTION rate_of_life_in_city(integer) RETURNS numeric
    LANGUAGE sql
    RETURN (SELECT ((city.development * game.ecorate) / 100) FROM ((city JOIN planet ON ((city.planetid = planet.id))) JOIN game ON ((planet.gameid = game.id))) WHERE (city.id = $1));

    CREATE OR REPLACE FUNCTION rate_of_life_in_planet(integer) RETURNS numeric
    LANGUAGE sql
    RETURN (SELECT avg((city.development * game.ecorate)) AS avg FROM ((city JOIN planet ON ((city.planetid = planet.id))) JOIN game ON ((planet.gameid = game.id))) GROUP BY planet.id HAVING (planet.id = $1));

    CREATE OR REPLACE PROCEDURE send_sanctions(IN integer, IN integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE is_sent BOOL;
                cur_round INT;
                game INT;
        BEGIN
            SELECT t.game INTO game FROM Planet WHERE id=$1;
            SELECT t.round INTO cur_round FROM Game WHERE id=game;
            is_sent := EXISTS(SELECT * FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Sanctions');
            IF is_sent THEN
                DELETE FROM Orders WHERE planetid=$1 AND argument=$2 AND action='Sanctions';
            ELSE
                INSERT INTO Orders (action, planetid, argument) VALUES ('Sanctions', $1, $2);
            END IF;
        END;
    $_$;

    CREATE OR REPLACE PROCEDURE start_new_round(IN gameid integer)
        LANGUAGE plpgsql
        AS $_$
        DECLARE gstatus gamestatus;
        BEGIN
            SELECT status INTO gstatus FROM Game WHERE id=$1;
            IF gstatus = 'Meeting' THEN
                UPDATE Planet SET balance=balance+planet_income(id) WHERE Planet.gameid=$1;
            END IF;
            IF gstatus = 'Negotiations' THEN
                RAISE EXCEPTION 'SRI';
            ELSE
                UPDATE Game SET round=COALESCE(round, 0) + 1, status='Negotiations' WHERE id=$1;
            END IF;
        END;
    $_$;

END$$;



