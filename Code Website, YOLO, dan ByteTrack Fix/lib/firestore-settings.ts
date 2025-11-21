import { doc, getDoc, setDoc, serverTimestamp } from "firebase/firestore";
import { db } from "./firebase";
import { AppConfig } from "./types";

// Collection and document ID for settings
const SETTINGS_COLLECTION = "settings";
const SETTINGS_DOC_ID = "app_config";

/**
 * Save application settings to Firestore
 */
export async function saveSettings(config: AppConfig): Promise<boolean> {
  try {
    const settingsRef = doc(db, SETTINGS_COLLECTION, SETTINGS_DOC_ID);
    
    await setDoc(settingsRef, {
      ...config,
      updated_at: serverTimestamp(),
      created_at: serverTimestamp() // Will only be set on first save
    }, { merge: true }); // Use merge to preserve created_at on updates
    
    return true;
  } catch (error) {
    console.error("❌ Error saving settings to Firestore:", error);
    return false;
  }
}

/**
 * Load application settings from Firestore
 */
export async function loadSettings(): Promise<AppConfig | null> {
  try {
    const settingsRef = doc(db, SETTINGS_COLLECTION, SETTINGS_DOC_ID);
    const settingsSnap = await getDoc(settingsRef);
    
    if (settingsSnap.exists()) {
      const data = settingsSnap.data();
      
      // Remove Firestore metadata before returning
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { updated_at, created_at, ...settings } = data;
      
      return settings as AppConfig;
    } else {
      return null;
    }
  } catch (error) {
    console.error("❌ Error loading settings from Firestore:", error);
    return null;
  }
}

/**
 * Check if settings exist in Firestore
 */
export async function settingsExist(): Promise<boolean> {
  try {
    const settingsRef = doc(db, SETTINGS_COLLECTION, SETTINGS_DOC_ID);
    const settingsSnap = await getDoc(settingsRef);
    return settingsSnap.exists();
  } catch (error) {
    console.error("❌ Error checking if settings exist:", error);
    return false;
  }
}