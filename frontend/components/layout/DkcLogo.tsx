/**
 * DkcLogo — DKC 57 Video Clipper brand mark (original DKC 57 asset).
 * Black / dark gray / red / white "DARKNIGHT" identity.
 */
export function DkcLogo({ size = 40 }: { size?: number }) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 64 64"
            fill="none"
            role="img"
            aria-label="DKC 57 Video Clipper"
        >
            <rect width="64" height="64" rx="14" fill="#0a0a0c" />
            <rect x="2.5" y="2.5" width="59" height="59" rx="12" stroke="#e11d48" strokeWidth="3" />
            <text
                x="32"
                y="30"
                textAnchor="middle"
                fontFamily="Arial, Helvetica, sans-serif"
                fontWeight="bold"
                fontSize="17"
                fill="#fafafa"
            >
                DKC
            </text>
            <rect x="18" y="34" width="28" height="2.5" rx="1.25" fill="#e11d48" />
            <text
                x="32"
                y="52"
                textAnchor="middle"
                fontFamily="Arial, Helvetica, sans-serif"
                fontWeight="bold"
                fontSize="15"
                fill="#e11d48"
            >
                57
            </text>
        </svg>
    );
}
