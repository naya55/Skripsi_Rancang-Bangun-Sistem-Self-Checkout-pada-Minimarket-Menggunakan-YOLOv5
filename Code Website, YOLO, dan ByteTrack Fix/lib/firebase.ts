import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";
import { getAnalytics } from "firebase/analytics";

const firebaseConfig = {
  apiKey: "AIzaSyD-7idygs9VpHO9VdzT0II2_1dc34QCQ24",
  authDomain: "naya-4a83a.firebaseapp.com",
  projectId: "naya-4a83a",
  storageBucket: "naya-4a83a.firebasestorage.app",
  messagingSenderId: "822821636809",
  appId: "1:822821636809:web:fa26417692de1a096cdb18",
  measurementId: "G-WLXPLHSVFD"
};

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
export const db = getFirestore(app);

let analytics: unknown = null;
if (typeof window !== "undefined") {
  analytics = getAnalytics(app);
}

export { analytics };
export default app;