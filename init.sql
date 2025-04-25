-- Create the role only if it doesn't exist
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'rocket') THEN
      CREATE ROLE rocket WITH LOGIN PASSWORD 'rocket123';
   END IF;
END
$$;

ALTER ROLE rocket CREATEDB;

-- Create the database only if it doesn't exist
SELECT 'CREATE DATABASE rocket_launch_genai'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'rocket_launch_genai')\gexec

-- Connect to the database
\c rocket_launch_genai

-- Grant usage and create on the public schema explicitly
GRANT USAGE, CREATE ON SCHEMA public TO rocket;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- Create cosine_similarity function for JSON and numeric array
CREATE OR REPLACE FUNCTION cosine_similarity(vector1 json, vector2 numeric[])
RETURNS float AS $$
DECLARE
    dotproduct float := 0.0;
    norm1 float := 0.0;
    norm2 float := 0.0;
    i int;
    v1 float[];
    elem_val float;
BEGIN
    -- Initialize v1 array with the correct size
    v1 := array_fill(0::float, ARRAY[array_length(vector2, 1)]);
    
    -- Manually extract values from JSON array to avoid parsing issues
    i := 1;
    FOR elem_val IN 
        SELECT (elem->>'value')::float 
        FROM json_array_elements(vector1) WITH ORDINALITY AS t(elem, idx)
    LOOP
        v1[i] := elem_val;
        i := i + 1;
        IF i > array_length(vector2, 1) THEN
            EXIT; -- Stop if we go beyond array bounds
        END IF;
    END LOOP;
    
    -- Alternative parsing method as fallback if the array is empty
    IF i = 1 THEN
        i := 1;
        FOR elem_val IN 
            SELECT elem::float 
            FROM json_array_elements_text(vector1) WITH ORDINALITY AS t(elem, idx)
        LOOP
            v1[i] := elem_val;
            i := i + 1;
            IF i > array_length(vector2, 1) THEN
                EXIT; -- Stop if we go beyond array bounds
            END IF;
        END LOOP;
    END IF;
    
    -- Check if dimensions match
    IF array_length(v1, 1) != array_length(vector2, 1) THEN
        RAISE NOTICE 'Vector dimensions do not match: % and %', array_length(v1, 1), array_length(vector2, 1);
        RETURN 0.0; -- Return 0 instead of error for robustness
    END IF;

    -- Calculate dot product and norms
    FOR i IN 1..array_length(v1, 1) LOOP
        dotproduct := dotproduct + (v1[i] * vector2[i]);
        norm1 := norm1 + (v1[i] * v1[i]);
        norm2 := norm2 + (vector2[i] * vector2[i]);
    END LOOP;

    -- Return cosine similarity
    IF norm1 = 0.0 OR norm2 = 0.0 THEN
        RETURN 0.0;
    ELSE
        RETURN dotproduct / (sqrt(norm1) * sqrt(norm2));
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Grant privileges (safe to run multiple times)
GRANT ALL PRIVILEGES ON DATABASE rocket_launch_genai TO rocket;
GRANT ALL ON SCHEMA public TO rocket; -- Grant privileges on the public schema
GRANT ALL ON ALL TABLES IN SCHEMA public TO rocket; -- Grant on existing tables
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO rocket; -- Grant on existing sequences
GRANT EXECUTE ON FUNCTION cosine_similarity(json, numeric[]) TO rocket; -- Grant execute on our new function

-- Optional: Ensure future objects are also granted
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO rocket;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO rocket;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO rocket; -- Add for functions/procedures if needed
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TYPES TO rocket; -- Add for types 