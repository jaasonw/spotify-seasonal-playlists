export const dynamic = "force-dynamic";
import SpotifyWebApi from "spotify-web-api-node";
import PocketBase from "pocketbase";

interface AuthToken {
  user_id: string;
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token: string;
  scope: string;
}

async function initUser(pb: PocketBase, user_id: string) {
  const record = await pb.collection("users").getList(1, 1, {
    filter: `user_id = "${user_id}"`,
  });
  if (record["items"].length == 0) {
    await pb.collection("user").create({
      user_id: user_id,
    });
  } else {
    await pb.collection("user").update(record["items"][0]["id"], {
      active: true,
    });
  }
}

async function initToken(pb: PocketBase, token: AuthToken) {
  const record = await pb.collection("tokens").getList(1, 1, {
    filter: `user_id = "${token["user_id"]}"`,
  });
  // if the user doesnt have a token, create it
  if (record["items"].length == 0) {
    await pb.collection("tokens").create(token);
  } else {
    await pb.collection("tokens").update(record["items"][0]["id"], token);
  }
}

async function storeToken(token: any) {
  const pb = new PocketBase(process.env.pocketbase_url);
  await pb.admins.authWithPassword(
    process.env.pocketbase_username ?? "",
    process.env.pocketbase_password ?? ""
  );
  await Promise.all([initUser(pb, token["user_id"]), initToken(pb, token)]);
}

async function authorizationCodeGrant(auth_code: string) {
  const spotifyApi = new SpotifyWebApi({
    redirectUri: process.env.redirect_uri,
    clientId: process.env.client_id,
    clientSecret: process.env.client_secret,
  });
  const token = await spotifyApi.authorizationCodeGrant(auth_code ?? "");
  spotifyApi.setAccessToken(token["body"]["access_token"]);
  const user = await spotifyApi.getMe();
  console.log(user["body"]);
  console.log(token["body"]);
  (token["body"] as AuthToken)["user_id"] = user["body"]["id"] ?? "";
  return token["body"];
}

export default async function SearchBar({
  params,
  searchParams,
}: {
  params: { slug: string };
  searchParams: { [key: string]: string };
}) {
  // await authorizationCodeGrant();
  // await storeToken("asdfsaf");
  if (!searchParams["code"]) {
    return <>no code</>;
  }
  const code = await authorizationCodeGrant(searchParams["code"] ?? "");
  // await storeToken(code);
  console.log(code);
  // return <>{JSON.stringify(code)}</>;
  return <>hello</>;
}
