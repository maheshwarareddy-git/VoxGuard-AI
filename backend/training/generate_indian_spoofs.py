import asyncio
import os
import edge_tts

BASE_DIR = r"c:\Users\mahesh\Desktop\VoxGuard"
OUT_DIR = os.path.join(BASE_DIR, "training_data", "ai_online")
os.makedirs(OUT_DIR, exist_ok=True)

# Realistic Indian scam, KYC fraud, OTP extortion, and banking impersonation scripts
SCRIPTS = [
    # ── Hindi Fraud & Impersonation (hi-IN) ──
    ("hi-IN-MadhurNeural", "hindi", "नमस्कार, मैं भारतीय स्टेट बैंक के मुख्य सुरक्षा कार्यालय से सीनियर मैनेजर बोल रहा हूँ। आपके खाते पर संदिग्ध लेन-देन देखा गया है।"),
    ("hi-IN-MadhurNeural", "hindi", "तुरंत अपना खाता चालू रखने के लिए अपने फोन पर आया हुआ छह अंकों का वन टाइम पासवर्ड मुझे बताएं।"),
    ("hi-IN-SwaraNeural", "hindi", "नमस्ते, आपका क्रेडिट कार्ड आज रात बारह बजे ब्लॉक कर दिया जाएगा। इसे चालू रखने के लिए अपनी जन्मतिथि और कार्ड नंबर सत्यापित करें।"),
    ("hi-IN-SwaraNeural", "hindi", "बधाई हो, आपका नाम प्रधान मंत्री आवास योजना की अंतिम लकी ड्रा सूची में चुना गया है। रजिस्ट्रेशन शुल्क तुरंत जमा करें।"),
    ("hi-IN-MadhurNeural", "hindi", "अरे भाई, मैं अस्पताल से बोल रहा हूँ, दोस्त का बहुत गंभीर एक्सीडेंट हो गया है, तुरंत इस नंबर पर बीस हज़ार रुपये गूगल पे कर दो।"),
    ("hi-IN-SwaraNeural", "hindi", "बिजली विभाग की सूचना: आज शाम आठ बजे आपका बिजली कनेक्शन काट दिया जाएगा। बिल अपडेट करने के लिए तुरंत इस नंबर पर कॉल करें।"),
    ("hi-IN-MadhurNeural", "hindi", "सर, आपका सिम कार्ड चौबीस घंटे में निष्क्रिय हो जाएगा। ई-केवाईसी पूरा करने के लिए अपना आधार नंबर और ओटीपी साझा करें।"),
    ("hi-IN-SwaraNeural", "hindi", "हेलो, मैं इनकम टैक्स डिपार्टमेंट से असिस्टेंट कमिश्नर बात कर रही हूँ। आपके खिलाफ टैक्स चोरी का नोटिस जारी किया गया है।"),
    ("hi-IN-MadhurNeural", "hindi", "आपका पार्सल मुंबई कस्टम्स द्वारा जब्त कर लिया गया है। गिरफ्तारी से बचने के लिए तुरंत पेनल्टी राशि ट्रांसफर करें।"),
    ("hi-IN-SwaraNeural", "hindi", "मैं पेटीएम कस्टमर सपोर्ट से बात कर रही हूँ। आपका वॉलेट रिवॉर्ड पॉइंट एक्सपायर हो रहा है, क्लेम करने के लिए लिंक पर क्लिक करें।"),

    # ── Telugu Fraud & Impersonation (te-IN) ──
    ("te-IN-MohanNeural", "telugu", "నమస్కారం, నేను స్టేట్ బ్యాంక్ ఆఫ్ ఇండియా హెడ్ ఆఫీస్ నుండి మేనేజర్ మాట్లాడుతున్నాను. మీ అకౌంట్ వెంటనే బ్లాక్ చేయబడుతుంది."),
    ("te-IN-MohanNeural", "telugu", "మీ ఖాతా రద్దు కాకుండా ఉండాలంటే మీ మొబైల్ కి వచ్చిన ఆరు అంకెల ఓటీపీని వెంటనే చెప్పండి."),
    ("te-IN-ShrutiNeural", "telugu", "హలో, మీ క్రెడిట్ కార్డు రివార్డు పాయింట్లు ఈరోజే ముగుస్తున్నాయి. నగదుగా మార్చుకోవడానికి మీ కార్డు వివరాలు చెప్పండి."),
    ("te-IN-ShrutiNeural", "telugu", "అభినందనలు! మీరు లక్కీ డ్రాలో పది లక్షల రూపాయల బహుమతి గెలుచుకున్నారు. క్లెయిమ్ చేసుకోవడానికి ప్రాసెసింగ్ ఫీజు చెల్లించండి."),
    ("te-IN-MohanNeural", "telugu", "అరేయ్ నేను హాస్పిటల్ లో ఉన్నాను రా, అర్జెంట్ గా ఆపరేషన్ చేయాలి, వెంటనే పది వేల రూపాయలు ఫోన్ పే చేయ్."),
    ("te-IN-ShrutiNeural", "telugu", "విద్యుత్ శాఖ హెచ్చరిక: గత నెల బిల్లు చెల్లించనందున ఈరోజు రాత్రి మీ కరెంట్ సరఫరా నిలిపివేయబడుతుంది."),
    ("te-IN-MohanNeural", "telugu", "మీ సిమ్ కార్డు ఈకేవైసీ వెరిఫికేషన్ పెండింగ్‌లో ఉంది. వెంటనే ఆధార్ నంబర్ మరియు ఓటీపీని వెరిఫై చేయండి."),
    ("te-IN-ShrutiNeural", "telugu", "నేను పోలీసు హెడ్ క్వార్టర్స్ నుండి మాట్లాడుతున్నాను, మీ పేరుతో కొరియర్ పార్సిల్ లో అనుమానాస్పద వస్తువులు దొరికాయి."),
    ("te-IN-MohanNeural", "telugu", "మీ గూగుల్ పే అకౌంట్ సెక్యూరిటీ అప్‌డేట్ చేయాలి, లేకపోతే లావాదేవీలు ఆగిపోతాయి. వెంటనే వివరాలు నమోదు చేయండి."),
    ("te-IN-ShrutiNeural", "telugu", "డియర్ కస్టమర్, మీ బ్యాంక్ ఖాతా కేవైసీ గడువు ముగిసింది. అకౌంట్ హోల్డ్ కాకుండా ఉండటానికి వెంటనే స్పందించండి."),

    # ── Indian English Impersonation (en-IN) ──
    ("en-IN-PrabhatNeural", "indian_en", "Good afternoon sir, this is Senior Inspector Rajesh Sharma calling from Delhi Police Cyber Crime Branch regarding your bank fraud complaint."),
    ("en-IN-PrabhatNeural", "indian_en", "I am calling from Union Bank Security Cell. We detected an unauthorized international transaction of fifty thousand rupees on your debit card."),
    ("en-IN-NeerjaNeural", "indian_en", "Dear customer, your electricity connection will be disconnected tonight at eight PM because previous month bill was not updated."),
    ("en-IN-NeerjaNeural", "indian_en", "Hello, I am calling from Mumbai Airport Customs authority. A suspicious consignment carrying illegal items addressed to your name has been detained."),
    ("en-IN-PrabhatNeural", "indian_en", "Your pan card is not linked with your primary savings account. Please share the six-digit verification code to avoid account suspension."),
    ("en-IN-NeerjaNeural", "indian_en", "Congratulations! You have been shortlisted for an executive remote job with Amazon India offering forty thousand rupees per month."),
    ("en-IN-PrabhatNeural", "indian_en", "Hi bro, my phone got stolen and I am stuck at the highway petrol pump. Please send five thousand rupees urgently on this Google Pay number."),
    ("en-IN-NeerjaNeural", "indian_en", "This is an automated call from State Bank of India. Your credit card reward points are expiring today. Press one to redeem into bank account."),
    ("en-IN-PrabhatNeural", "indian_en", "Your mobile SIM card KYC is incomplete as per telecom regulatory orders. To avoid outgoing call blockage, verify your credentials immediately."),
    ("en-IN-NeerjaNeural", "indian_en", "Attention customer, your Netflix subscription payment has failed. Update your card CVV immediately to continue streaming services.")
]

async def generate_single(voice: str, lang: str, text: str, idx: int):
    filename = f"indian_spoof_{lang}_{voice.split('-')[1].lower()}_{idx:02d}.mp3"
    filepath = os.path.join(OUT_DIR, filename)
    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
        return filename, False
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filepath)
        return filename, True
    except Exception as e:
        print(f"Error generating {filename}: {e}")
        return filename, False

async def main():
    print("=" * 75)
    print("VOXGUARD INDIAN-LANGUAGE NEURAL SPOOF GENERATOR (EDGE-TTS)")
    print("=" * 75)
    tasks = []
    for i, (voice, lang, text) in enumerate(SCRIPTS):
        tasks.append(generate_single(voice, lang, text, i + 1))
    
    results = await asyncio.gather(*tasks)
    created = sum(1 for _, was_created in results if was_created)
    total = len(results)
    print(f"\n[COMPLETE] Generated {created} new Indian-language neural spoof audio files ({total} total).")
    print(f"  Target directory: {OUT_DIR}")

if __name__ == "__main__":
    asyncio.run(main())
