CREATE TABLE Users(
  "id" TEXT,
  "update_count" INTEGER DEFAULT 0,
  "error_count" INTEGER DEFAULT 0,
  "last_error" TEXT DEFAULT "",
  "last_playlist" TEXT DEFAULT "",
  "last_update" TEXT DEFAULT "",
  "active" TEXT DEFAULT "",
)

CREATE TABLE Tokens (
  "id" text,
  "access_token" text,
  "token_type" text,
  "expires_in" integer,
  "refresh_token" text,
  "scope" text,
  "expires_at" integer
)

CREATE TABLE "errors" (
	"id"	TEXT,
	"error"	TEXT,
	PRIMARY KEY("id")
)

create index user_index on users(id);
create index token_index on tokens(id);