import {FC} from "react";
import {Text} from "@chakra-ui/react";
import { useTranslation } from "react-i18next";
import { relativeOnlineDate } from "utils/dateFormatter";

type UserStatusProps = {
    lastOnline: string | null;
};

export const OnlineStatus: FC<UserStatusProps> = ({lastOnline}) => {
    const { t } = useTranslation();

    return (
        <Text
            display="inline-block"
            fontSize="xs"
            fontWeight="medium"
            ml="2"
            color="gray.600"
            _dark={{
                color: "gray.400",
            }}
        >
            {relativeOnlineDate(lastOnline, t)}
        </Text>
    );
};
