import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import SignIn from "./components/SignIn";
import { token } from "./api/client";
import { DEMO_BUILD } from "./demo";
import "./index.css";

function Root() {
  // The token lives in localStorage, so a reload keeps you signed in. A 401
  // anywhere clears it, which flips this back to the sign-in screen.
  // The demo build has no auth server to sign in against, so it opens straight
  // onto the dashboard and reads from the bundled snapshot.
  const [signedIn, setSignedIn] = useState(() => DEMO_BUILD || Boolean(token.get()));

  if (!signedIn) return <SignIn onSignedIn={() => setSignedIn(true)} />;
  return <App />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
